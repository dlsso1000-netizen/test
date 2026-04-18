/* ============================================
   북마크 모듈 (localStorage 기반)
   - 채널 북마크: { id, title, thumbnail, addedAt }
   ============================================ */

const BOOKMARK_KEY = 'jh.bookmarks.v1';

const Bookmarks = {
  all() {
    try {
      return JSON.parse(localStorage.getItem(BOOKMARK_KEY) || '[]');
    } catch (_) {
      return [];
    }
  },
  has(id) {
    return this.all().some((b) => b.id === id);
  },
  add(item) {
    const list = this.all();
    if (list.some((b) => b.id === item.id)) return list;
    list.push({ ...item, addedAt: new Date().toISOString() });
    localStorage.setItem(BOOKMARK_KEY, JSON.stringify(list));
    return list;
  },
  remove(id) {
    const list = this.all().filter((b) => b.id !== id);
    localStorage.setItem(BOOKMARK_KEY, JSON.stringify(list));
    return list;
  },
  toggle(item) {
    return this.has(item.id) ? this.remove(item.id) : this.add(item);
  },
  clear() {
    localStorage.removeItem(BOOKMARK_KEY);
  },
};

window.Bookmarks = Bookmarks;
