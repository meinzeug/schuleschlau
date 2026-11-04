import 'dart:async';

import 'package:flutter/foundation.dart';

import 'api.dart';

class _CursorLoop implements Exception {
  const _CursorLoop();
}

class _NoticePage {
  final String? start, next;
  final List<Json> items;
  const _NoticePage(this.start, this.next, this.items);
}

/// Account-scoped cache. Only foreground GETs; no Firebase or generation here.
class NotificationInbox extends ChangeNotifier {
  final Api api;
  NotificationInbox(this.api);
  String? _account, _family, _session;
  int _generation = 0;
  int _readRevision = 0;
  final _readsInFlight = <String, Future<void>>{};
  bool _foreground = true, _loading = false, _loadingMore = false;
  bool _disposed = false;
  // The newest page stays visible; at most two older consecutive pages are
  // retained. Their starting cursor survives eviction and bounded refreshes.
  static const maxCachedPages = 3;
  // Keep error handling itself bounded even if a broken server returns an
  // unlimited stream of distinct cursors. A fresh refresh starts a new epoch.
  static const maxHistoryCursors = 2048;
  final _seenCursors = <String>{};
  List<_NoticePage> _pages = [];
  bool historyTrimmed = false;
  bool supportsPagination = false;
  String? nextCursor, moreError;
  Timer? _timer;
  List<Json> items = [];
  int unread = 0;
  int retentionDays = 30, itemLimit = 50;
  String? error;
  bool hasLoaded = false;
  bool get loading => _loading;
  bool get loadingMore => _loadingMore;

  void activate(String? account, {String? family, String? session}) {
    if (account == null) {
      family = null;
      session = null;
    }
    if (_account == account && _family == family && _session == session) return;
    _generation++;
    _readRevision = 0;
    _readsInFlight.clear();
    _account = account;
    _family = account == null ? null : family;
    _session = account == null ? null : session;
    items = [];
    unread = 0;
    retentionDays = 30;
    itemLimit = 50;
    error = null;
    hasLoaded = false;
    _loading = false;
    _loadingMore = false;
    _pages = [];
    _seenCursors.clear();
    historyTrimmed = false;
    supportsPagination = false;
    nextCursor = moreError = null;
    _timer?.cancel();
    if (account != null) {
      unawaited(refresh());
      _timer = Timer.periodic(const Duration(seconds: 45), (_) {
        if (_foreground) unawaited(refresh());
      });
    }
    notifyListeners();
  }

  void foreground(bool value) {
    final resume = value && !_foreground;
    _foreground = value;
    if (resume) unawaited(refresh());
  }

  Future<void> refresh() async {
    if (_disposed ||
        _account == null ||
        _loading ||
        _loadingMore ||
        !_foreground) {
      return;
    }
    final generation = _generation;
    final readRevision = _readRevision;
    var retryAfterRead = false;
    _loading = true;
    // Refresh can begin while a sibling (the bell) is being rebuilt on navigation.
    scheduleMicrotask(() {
      if (!_disposed && generation == _generation) notifyListeners();
    });
    try {
      final data = await api.get('/notifications/inbox?paginate=1');
      if (generation != _generation) return;
      if (readRevision != _readRevision) {
        // The old snapshot must not undo a receipt, but discarding it alone
        // can also hide newly arrived events until the next periodic refresh.
        retryAfterRead = true;
        return;
      }
      final head = _parsePage(data, null);
      final refreshedPages = <_NoticePage>[head];
      final refreshCursors = <String>{};
      final wantsHistory = data.containsKey('next_cursor') && _pages.length > 1;
      var cursor = historyTrimmed && wantsHistory ? _pages[1].start : head.next;
      while (wantsHistory &&
          refreshedPages.length < _pages.length &&
          cursor != null) {
        if (!refreshCursors.add(cursor)) throw const _CursorLoop();
        final query = Uri(queryParameters: {'paginate': '1', 'cursor': cursor})
            .query;
        final data = await api.get('/notifications/inbox?$query');
        if (_disposed || generation != _generation) return;
        if (readRevision != _readRevision) {
          retryAfterRead = true;
          return;
        }
        final page = _parsePage(data, cursor);
        if (page.next != null && refreshCursors.contains(page.next)) {
          throw const _CursorLoop();
        }
        refreshedPages.add(page);
        cursor = page.next;
      }
      _pages = refreshedPages;
      _seenCursors
        ..clear()
        ..addAll(refreshCursors);
      supportsPagination = data.containsKey('next_cursor');
      if (!supportsPagination || _pages.length == 1) historyTrimmed = false;
      _rebuildItems();
      final retention = data['retention_days'];
      final limit = data['limit'];
      retentionDays = retention is int && retention >= 1 && retention <= 365
          ? retention
          : 30;
      itemLimit = limit is int && limit >= 1 && limit <= 500 ? limit : 50;
      error = null;
      moreError = null;
      hasLoaded = true;
    } catch (_) {
      if (generation == _generation) {
        // A failed rights/source revalidation must not keep previously cached
        // private notices on screen as though they were still authorized.
        _pages = [];
        _seenCursors.clear();
        historyTrimmed = false;
        supportsPagination = false;
        items = [];
        unread = 0;
        nextCursor = moreError = null;
        hasLoaded = false;
        error = 'Neuigkeiten konnten nicht geladen werden. Bitte versuche es erneut.';
      }
    } finally {
      if (!_disposed && generation == _generation) {
        _loading = false;
        notifyListeners();
        if (!_disposed &&
            generation == _generation &&
            retryAfterRead &&
            _foreground) {
          unawaited(refresh());
        }
      }
    }
  }

  /// Explicit or scroll-triggered continuation. GET never creates events.
  Future<void> loadMore() async {
    final cursor = nextCursor;
    if (_disposed ||
        _account == null ||
        !_foreground ||
        _loading ||
        _loadingMore ||
        cursor == null) {
      return;
    }
    if (_seenCursors.length >= maxHistoryCursors) {
      moreError = 'Sehr viele Seiten geladen.';
      notifyListeners();
      return;
    }
    final generation = _generation;
    _loadingMore = true;
    moreError = null;
    notifyListeners();
    try {
      final query = Uri(queryParameters: {'paginate': '1', 'cursor': cursor})
          .query;
      Json? data;
      // A page requested before a successful read may contain an obsolete
      // duplicate. Retry once against the updated receipt instead of saving it.
      for (var attempt = 0; attempt < 2; attempt++) {
        final readRevision = _readRevision;
        final response = await api.get('/notifications/inbox?$query');
        if (_disposed || generation != _generation) return;
        if (readRevision == _readRevision) {
          data = response;
          break;
        }
      }
      if (data == null) throw StateError('Read state changed while loading');
      final page = _parsePage(data, cursor);
      if (page.next != null && _seenCursors.contains(page.next)) {
        throw const _CursorLoop();
      }
      _seenCursors.add(cursor);
      _pages.add(page);
      if (_pages.length > maxCachedPages) {
        // Keep the newest page and the two oldest consecutive pages in this
        // window. The second page records its own input cursor for refresh.
        _pages.removeAt(1);
        historyTrimmed = true;
      }
      _rebuildItems();
    } catch (error) {
      if (generation == _generation) {
        moreError = error is _CursorLoop
            ? 'Laden angehalten.'
            : 'Laden nicht möglich.';
      }
    } finally {
      if (!_disposed && generation == _generation) {
        _loadingMore = false;
        notifyListeners();
      }
    }
  }

  _NoticePage _parsePage(Json data, String? start) {
    final value = data['next_cursor'];
    final next = value is String && value.isNotEmpty ? value : null;
    if (next != null && (next == start || next.length > 512)) {
      throw const _CursorLoop();
    }
    return _NoticePage(
      start,
      next,
      (data['items'] as List? ?? [])
          .map((raw) => Map<String, dynamic>.from(raw))
          .toList(),
    );
  }

  void _rebuildItems() {
    final seen = <Object?>{};
    items = [
      for (final page in _pages)
        for (final item in page.items)
          if (seen.add(item['id'])) item,
    ];
    nextCursor = _pages.isEmpty ? null : _pages.last.next;
    unread = items.where((row) => row['read'] != true).length;
  }

  /// Discard a scrolled history window and return to the latest notifications.
  Future<void> showLatest() async {
    if (_disposed || _account == null || _loading || _loadingMore) return;
    _pages = [];
    _seenCursors.clear();
    historyTrimmed = false;
    items = [];
    unread = 0;
    nextCursor = null;
    moreError = null;
    hasLoaded = false;
    notifyListeners();
    await refresh();
  }

  Future<void> markRead(List<String> ids) async {
    if (_disposed || _account == null || ids.isEmpty) return;
    final generation = _generation;
    final ownUnread = items
        .where((item) => item['read'] != true)
        .map((item) => item['id'])
        .whereType<String>()
        .toSet();
    final requested = ids.toSet().intersection(ownUnread);
    if (requested.isEmpty) return;
    final waiting = <Future<void>>{
      for (final id in requested) ?_readsInFlight[id],
    };
    final fresh = requested
        .where((id) => !_readsInFlight.containsKey(id))
        .toList();
    if (fresh.isNotEmpty) {
      // An older GET may never undo a pending or successful acknowledgement.
      _readRevision++;
      Future<void> send() async {
        await api.post('/notifications/inbox/read', {'ids': fresh});
        if (_disposed || generation != _generation) return;
        _readRevision++;
        // The same event may occur in overlapping pages after concurrent
        // inserts. Update every cached copy before a window rotation can expose
        // a formerly hidden stale copy.
        for (final page in _pages) {
          for (final item in page.items) {
            if (fresh.contains(item['id'])) item['read'] = true;
          }
        }
        _rebuildItems();
        notifyListeners();
      }

      late final Future<void> pending;
      pending = send().whenComplete(() {
        if (generation != _generation) return;
        for (final id in fresh) {
          if (identical(_readsInFlight[id], pending)) _readsInFlight.remove(id);
        }
      });
      for (final id in fresh) {
        _readsInFlight[id] = pending;
      }
      waiting.add(pending);
    }
    await Future.wait(waiting);
  }

  void clear() => activate(null);
  @override
  void dispose() {
    _disposed = true;
    _generation++;
    _timer?.cancel();
    super.dispose();
  }
}
