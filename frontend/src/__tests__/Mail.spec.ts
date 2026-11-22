import { describe, expect, it } from "vitest";
import { addresses, composeHtml, displayName, hasRemoteImages, mailDocument, replyFields, sanitizeMail, type MailMessage } from "@/components/app/mail/mail";

const msg = (over: Partial<MailMessage> = {}): MailMessage => ({
  id: "1", folder: "5", thread: "", subject: "Quote", summary: "", from: '"Asha Rai" <asha@client.test>', sender: "Asha Rai",
  to: "me@thimitech.com, bob@client.test", cc: "<carol@client.test>", received: 1_700_000_000_000, unread: false,
  has_attachments: false, flagged: false, content: "<p>Original</p>", attachments: [], ...over,
});

describe("mail helpers", () => {
  it("parses Zoho address strings", () => {
    expect(addresses('"A" <a@x.com>, b@y.org, <a@x.com>')).toEqual(["a@x.com", "b@y.org"]);
    expect(displayName('"Asha Rai" <asha@client.test>')).toBe("Asha Rai");
    expect(displayName("<asha@client.test>")).toBe("asha@client.test");
  });

  it("prefills reply, reply-all and forward without my own address", () => {
    const me = ["me@thimitech.com"];
    expect(replyFields(msg(), "reply", me)).toEqual({ to: "asha@client.test", cc: "", subject: "Re: Quote" });
    expect(replyFields(msg(), "replyall", me)).toEqual({ to: "asha@client.test, bob@client.test", cc: "carol@client.test", subject: "Re: Quote" });
    expect(replyFields(msg({ subject: "RE: Quote" }), "reply", me).subject).toBe("RE: Quote");
    expect(replyFields(msg(), "forward", me)).toEqual({ to: "", cc: "", subject: "Fwd: Quote" });
    // replying to something I sent goes back to its recipients
    expect(replyFields(msg({ from: "me@thimitech.com" }), "reply", me).to).toBe("me@thimitech.com, bob@client.test");
  });

  it("escapes what I type and quotes the original", () => {
    const html = composeHtml("1 < 2\nok", msg({ content: '<p onclick="x()">Original</p><script>bad()</script>' }), "reply");
    expect(html).toContain("1 &lt; 2<br>ok");
    expect(html).toContain("<blockquote");
    expect(html).not.toContain("onclick");
    expect(html).not.toContain("<script");
  });

  it("strips active content and blocks remote images until allowed", () => {
    const dirty = '<img src="https://track.test/p.gif" onerror="x()"><form><input></form><a href="javascript:alert(1)">x</a>';
    const clean = sanitizeMail(dirty);
    expect(clean).not.toMatch(/onerror|<form|<input|javascript:/);
    expect(hasRemoteImages(dirty)).toBe(true);
    expect(hasRemoteImages('<img src="data:image/png;base64,AA">')).toBe(false);
    expect(mailDocument(dirty, false)).toContain("img-src data: cid:;");
    expect(mailDocument(dirty, true)).toContain("img-src data: cid: https: http:;");
  });
});
