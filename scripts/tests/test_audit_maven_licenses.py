import urllib.error

import pytest

from scripts.audit_maven_licenses import (
    FLUTTER_REPOSITORY,
    JITPACK_REPOSITORY,
    REPOSITORIES,
    find_pom,
    inspect,
    parse_pom,
    safe_gav,
)


def pom(group='org.example', artifact='app', version='1.0', license_xml='', parent_xml=''):
    return (f'<project xmlns="http://maven.apache.org/POM/4.0.0">'
            f'<groupId>{group}</groupId><artifactId>{artifact}</artifactId><version>{version}</version>'
            f'{parent_xml}{license_xml}</project>').encode()


LICENSE = '<licenses><license><name>Apache-2.0</name><url>https://example.invalid/license</url></license></licenses>'
PARENT = '<parent><groupId>org.example</groupId><artifactId>parent</artifactId><version>1.0</version></parent>'


def test_fixed_repositories_then_direct_license_and_hash():
    urls = []

    def fetch(url):
        urls.append(url)
        return None if url.startswith(REPOSITORIES[0]) else pom(license_xml=LICENSE)

    result = inspect(('org.example:app', '1.0'), fetch)
    assert result['status'] == 'declared'
    assert result['licenses'][0]['name'] == 'Apache-2.0'
    assert len(result['chain'][0]['sha256']) == 64
    assert len(urls) == 2
    assert urls[0].startswith(REPOSITORIES[0])
    assert urls[1].startswith(REPOSITORIES[1])


def test_parent_inheritance_is_explicit_and_sourced():
    def fetch(url):
        return pom(artifact='parent', license_xml=LICENSE) if '/parent/' in url else pom(parent_xml=PARENT)

    result = inspect(('org.example:app', '1.0'), fetch)
    assert result['status'] == 'parent_declared'
    assert [item['coordinate'] for item in result['chain']] == ['org.example:app:1.0', 'org.example:parent:1.0']


def test_legacy_namespace_free_pom_is_supported():
    old_pom = pom(license_xml=LICENSE).replace(b' xmlns="http://maven.apache.org/POM/4.0.0"', b'')
    assert inspect(('org.example:app', '1.0'), lambda _: old_pom)['status'] == 'declared'


def test_absent_license_pom_or_unresolved_property_is_not_success():
    assert inspect(('org.example:app', '1.0'), lambda _: pom())['status'] == 'not_declared'
    assert inspect(('org.example:app', '1.0'), lambda _: None)['status'] == 'pom_unavailable'
    dynamic = '<licenses><license><name>${license}</name></license></licenses>'
    assert inspect(('org.example:app', '1.0'), lambda _: pom(license_xml=dynamic))['status'] == 'unresolved_property'


def test_parent_cycle_is_rejected():
    cyclic = '<parent><groupId>org.example</groupId><artifactId>app</artifactId><version>1.0</version></parent>'
    with pytest.raises(ValueError, match='cycle'):
        inspect(('org.example:app', '1.0'), lambda _: pom(parent_xml=cyclic))


@pytest.mark.parametrize('gav', [('../evil', 'app', '1'), ('org.example', '../app', '1'),
                                  ('org.example', 'app', '${version}'), ('org.example', 'app', '')])
def test_unsafe_coordinates_are_rejected(gav):
    with pytest.raises(ValueError, match='coordinate'):
        safe_gav(*gav)


def test_unsafe_or_wrong_pom_is_rejected():
    with pytest.raises(ValueError, match='Unsafe'):
        parse_pom(b'<!DOCTYPE project [<!ENTITY x "hello">]><project>&x;</project>', ('g', 'a', 'v'))
    with pytest.raises(ValueError, match='root'):
        parse_pom(b'<html/>', ('g', 'a', 'v'))
    with pytest.raises(ValueError, match='mismatch'):
        parse_pom(pom(), ('org.example', 'different', '1.0'))


def test_repository_failure_is_not_treated_as_absence():
    def failed(url):
        raise urllib.error.HTTPError(url, 503, 'unavailable', {}, None)

    with pytest.raises(urllib.error.HTTPError):
        find_pom(('org.example', 'app', '1.0'), failed)


@pytest.mark.parametrize(('gav', 'last'), [
    (('io.flutter', 'engine', '1.0'), FLUTTER_REPOSITORY),
    (('com.github.davidliu', 'audioswitch', '1.0'), JITPACK_REPOSITORY),
])
def test_specific_additional_repository_is_bounded(gav, last):
    seen = []

    def fetch(url):
        seen.append(url)
        return None

    assert find_pom(gav, fetch) == (None, None)
    assert len(seen) == 3
    assert seen[-1].startswith(last)
