import DOMPurify from "dompurify";

export interface Sender {
  address: string;
  name: string;
}
export interface MailStatus {
  configured: boolean;
  connected: boolean;
  needs_reconnect: boolean;
  email: string;
  display_name: string;
  send_from: Sender[];
}
export interface Folder {
  id: string;
  name: string;
  type: string;
  path: string;
}
export interface MailSummary {
  id: string;
  folder: string;
  thread: string;
  subject: string;
  summary: string;
  from: string;
  sender: string;
  to: string;
  cc: string;
  received: number | null;
  unread: boolean;
  has_attachments: boolean;
  flagged: boolean;
}
export interface MailAttachment {
  id: string;
  name: string;
  size: number | null;
}
export interface MailMessage extends MailSummary {
  content: string;
  attachments: MailAttachment[];
}
export interface Upload {
  storeName: string;
  attachmentPath: string;
  attachmentName: string;
}
export type ComposeMode = "new" | "reply" | "replyall" | "forward";

const EMAIL = /[^\s<>,;"'()]+@[^\s<>,;"'()]+\.[^\s<>,;"'()]+/g;

/** Bare addresses found in a Zoho address string ("Name" <a@b.com>, c@d.com …). */
export function addresses(value: string): string[] {
  const seen = new Set<string>();
  return (value.match(EMAIL) || []).filter((a) => {
    const k = a.toLowerCase();
    return seen.has(k) ? false : (seen.add(k), true);
  });
}

/** "Asha Rai" from `"Asha Rai" <asha@x.com>`, else the address itself. */
export function displayName(value: string, fallback = ""): string {
  const named = value.match(/^\s*"?([^"<]+?)"?\s*</);
  if (named?.[1]) return named[1].trim();
  return addresses(value)[0] || fallback || value;
}

const KTM = "Asia/Kathmandu";
export function shortDate(ms: number | null, now = Date.now()): string {
  if (!ms) return "";
  const d = new Date(ms);
  const day = (t: number) => new Intl.DateTimeFormat("en-CA", { timeZone: KTM }).format(new Date(t));
  if (day(ms) === day(now)) return new Intl.DateTimeFormat("en-GB", { timeZone: KTM, hour: "2-digit", minute: "2-digit" }).format(d);
  const sameYear = new Date(ms).getFullYear() === new Date(now).getFullYear();
  return new Intl.DateTimeFormat("en-GB", { timeZone: KTM, day: "numeric", month: "short", year: sameYear ? undefined : "numeric" }).format(d);
}
export function longDate(ms: number | null): string {
  if (!ms) return "";
  return new Intl.DateTimeFormat("en-GB", { timeZone: KTM, dateStyle: "medium", timeStyle: "short" }).format(new Date(ms));
}
export function fileSize(bytes: number | null): string {
  if (bytes == null) return "";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

/** Sanitized email HTML (no scripts, forms or event handlers). Rendered inside a sandboxed iframe by MailBody. */
export function sanitizeMail(html: string): string {
  return DOMPurify.sanitize(html, {
    ADD_TAGS: ["style"],
    FORBID_TAGS: ["form", "input", "button", "textarea", "select", "option", "meta", "link", "base"],
    FORBID_ATTR: ["srcset"],
  });
}

/** Does the message load anything from the internet (tracking pixels, hosted images)? */
export function hasRemoteImages(html: string): boolean {
  return /<img[^>]+src\s*=\s*["']?\s*(https?:)?\/\//i.test(html) || /url\(\s*["']?\s*(https?:)?\/\//i.test(html);
}

/** Full document for the iframe. The CSP blocks remote content unless `images` is on. */
export function mailDocument(html: string, images: boolean): string {
  const img = images ? "data: cid: https: http:" : "data: cid:";
  return `<!doctype html><html><head><meta charset="utf-8">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; img-src ${img}; style-src 'unsafe-inline'; font-src data:${images ? " https:" : ""}">
<base target="_blank">
<style>html{color-scheme:light}body{margin:0;padding:4px 2px;font:14px/1.55 system-ui,-apple-system,"Segoe UI",sans-serif;color:#1f2328;background:#fff;overflow-wrap:anywhere}img{max-width:100%;height:auto}blockquote{margin:0 0 0 .5em;padding-left:.8em;border-left:2px solid #d0d7de;color:#57606a}pre{white-space:pre-wrap}</style>
</head><body>${sanitizeMail(html)}</body></html>`;
}

const ESC: Record<string, string> = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" };
export const escapeHtml = (s: string) => s.replace(/[&<>"']/g, (c) => ESC[c]!);

/** What the person typed (plain text) as HTML, with the quoted original below it for replies/forwards. */
export function composeHtml(text: string, quote?: MailMessage, mode: ComposeMode = "new"): string {
  const body = `<div>${escapeHtml(text).replace(/\r?\n/g, "<br>")}</div>`;
  if (!quote || mode === "new") return body;
  const head =
    mode === "forward"
      ? `---------- Forwarded message ----------<br>From: ${escapeHtml(quote.from)}<br>Date: ${escapeHtml(longDate(quote.received))}<br>Subject: ${escapeHtml(quote.subject)}<br>To: ${escapeHtml(quote.to)}`
      : `On ${escapeHtml(longDate(quote.received))}, ${escapeHtml(quote.from)} wrote:`;
  return `${body}<br><div>${head}</div><blockquote style="margin:0 0 0 .5em;padding-left:.8em;border-left:2px solid #ccc">${sanitizeMail(quote.content)}</blockquote>`;
}

/** Prefilled recipients and subject for a reply, reply-all or forward. `me` = my own addresses (left out). */
export function replyFields(msg: MailMessage, mode: ComposeMode, me: string[]) {
  const mine = new Set(me.map((a) => a.toLowerCase()));
  const notMe = (list: string[]) => list.filter((a) => !mine.has(a.toLowerCase()));
  const prefix = mode === "forward" ? "Fwd: " : "Re: ";
  const subject = new RegExp(`^${prefix.trim()}`, "i").test(msg.subject) ? msg.subject : prefix + msg.subject;
  if (mode === "forward") return { to: "", cc: "", subject };
  const from = addresses(msg.from);
  if (mode === "reply") return { to: (notMe(from).length ? from : addresses(msg.to)).join(", "), cc: "", subject };
  const to = notMe([...from, ...addresses(msg.to)]);
  const cc = notMe(addresses(msg.cc)).filter((a) => !to.includes(a));
  return { to: to.join(", "), cc: cc.join(", "), subject };
}
