// The paid beta path is limited to the exact artificial family recorded by
// beta_live_signup_smoke.py. Never accept an arbitrary production family.
export function ownsArtificialBeta(account, journal) {
  const email = account?.credentials?.parent_username;
  const child = account?.credentials?.child_username;
  const match = typeof email === 'string' && email.match(/^[^+@]+\+schuleschlau-beta-qa-([a-f0-9]{20})@(?:gmail|googlemail)\.com$/i);
  return Boolean(match && child === `beta-qa-${match[1]}` &&
    account.normal_account === true && account.verified === true &&
    journal?.verified === true && journal.email === email &&
    journal.child === child && journal.child_id === account.child_id &&
    journal.user_id === account.user?.id &&
    journal.family_id === account.user?.families?.[0]?.id &&
    account.user?.families?.length === 1);
}

export function isArtificialFreeAccount(account) {
  return Boolean(account?.normal_account && account.verified &&
    /\+schulpilot-normal-qa-[a-f0-9]{12}@(?:gmail|googlemail)\.com$/i.test(account.credentials?.parent_username ?? ''));
}
