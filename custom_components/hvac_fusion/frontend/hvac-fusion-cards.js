/**
 * @license
 * Copyright 2019 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
var _a;
const t$1 = globalThis, e$2 = t$1.ShadowRoot && (void 0 === t$1.ShadyCSS || t$1.ShadyCSS.nativeShadow) && "adoptedStyleSheets" in Document.prototype && "replace" in CSSStyleSheet.prototype, s$2 = Symbol(), o$4 = /* @__PURE__ */ new WeakMap();
let n$3 = class n {
  constructor(t2, e2, o2) {
    if (this._$cssResult$ = true, o2 !== s$2) throw Error("CSSResult is not constructable. Use `unsafeCSS` or `css` instead.");
    this.cssText = t2, this.t = e2;
  }
  get styleSheet() {
    let t2 = this.o;
    const s2 = this.t;
    if (e$2 && void 0 === t2) {
      const e2 = void 0 !== s2 && 1 === s2.length;
      e2 && (t2 = o$4.get(s2)), void 0 === t2 && ((this.o = t2 = new CSSStyleSheet()).replaceSync(this.cssText), e2 && o$4.set(s2, t2));
    }
    return t2;
  }
  toString() {
    return this.cssText;
  }
};
const r$4 = (t2) => new n$3("string" == typeof t2 ? t2 : t2 + "", void 0, s$2), i$3 = (t2, ...e2) => {
  const o2 = 1 === t2.length ? t2[0] : e2.reduce((e3, s2, o3) => e3 + ((t3) => {
    if (true === t3._$cssResult$) return t3.cssText;
    if ("number" == typeof t3) return t3;
    throw Error("Value passed to 'css' function must be a 'css' function result: " + t3 + ". Use 'unsafeCSS' to pass non-literal values, but take care to ensure page security.");
  })(s2) + t2[o3 + 1], t2[0]);
  return new n$3(o2, t2, s$2);
}, S$1 = (s2, o2) => {
  if (e$2) s2.adoptedStyleSheets = o2.map((t2) => t2 instanceof CSSStyleSheet ? t2 : t2.styleSheet);
  else for (const e2 of o2) {
    const o3 = document.createElement("style"), n3 = t$1.litNonce;
    void 0 !== n3 && o3.setAttribute("nonce", n3), o3.textContent = e2.cssText, s2.appendChild(o3);
  }
}, c$2 = e$2 ? (t2) => t2 : (t2) => t2 instanceof CSSStyleSheet ? ((t3) => {
  let e2 = "";
  for (const s2 of t3.cssRules) e2 += s2.cssText;
  return r$4(e2);
})(t2) : t2;
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
const { is: i$2, defineProperty: e$1, getOwnPropertyDescriptor: h$1, getOwnPropertyNames: r$3, getOwnPropertySymbols: o$3, getPrototypeOf: n$2 } = Object, a$1 = globalThis, c$1 = a$1.trustedTypes, l$1 = c$1 ? c$1.emptyScript : "", p$1 = a$1.reactiveElementPolyfillSupport, d$1 = (t2, s2) => t2, u$1 = { toAttribute(t2, s2) {
  switch (s2) {
    case Boolean:
      t2 = t2 ? l$1 : null;
      break;
    case Object:
    case Array:
      t2 = null == t2 ? t2 : JSON.stringify(t2);
  }
  return t2;
}, fromAttribute(t2, s2) {
  let i2 = t2;
  switch (s2) {
    case Boolean:
      i2 = null !== t2;
      break;
    case Number:
      i2 = null === t2 ? null : Number(t2);
      break;
    case Object:
    case Array:
      try {
        i2 = JSON.parse(t2);
      } catch (t3) {
        i2 = null;
      }
  }
  return i2;
} }, f$1 = (t2, s2) => !i$2(t2, s2), b$1 = { attribute: true, type: String, converter: u$1, reflect: false, useDefault: false, hasChanged: f$1 };
Symbol.metadata ?? (Symbol.metadata = Symbol("metadata")), a$1.litPropertyMetadata ?? (a$1.litPropertyMetadata = /* @__PURE__ */ new WeakMap());
let y$1 = class y extends HTMLElement {
  static addInitializer(t2) {
    this._$Ei(), (this.l ?? (this.l = [])).push(t2);
  }
  static get observedAttributes() {
    return this.finalize(), this._$Eh && [...this._$Eh.keys()];
  }
  static createProperty(t2, s2 = b$1) {
    if (s2.state && (s2.attribute = false), this._$Ei(), this.prototype.hasOwnProperty(t2) && ((s2 = Object.create(s2)).wrapped = true), this.elementProperties.set(t2, s2), !s2.noAccessor) {
      const i2 = Symbol(), h2 = this.getPropertyDescriptor(t2, i2, s2);
      void 0 !== h2 && e$1(this.prototype, t2, h2);
    }
  }
  static getPropertyDescriptor(t2, s2, i2) {
    const { get: e2, set: r2 } = h$1(this.prototype, t2) ?? { get() {
      return this[s2];
    }, set(t3) {
      this[s2] = t3;
    } };
    return { get: e2, set(s3) {
      const h2 = e2 == null ? void 0 : e2.call(this);
      r2 == null ? void 0 : r2.call(this, s3), this.requestUpdate(t2, h2, i2);
    }, configurable: true, enumerable: true };
  }
  static getPropertyOptions(t2) {
    return this.elementProperties.get(t2) ?? b$1;
  }
  static _$Ei() {
    if (this.hasOwnProperty(d$1("elementProperties"))) return;
    const t2 = n$2(this);
    t2.finalize(), void 0 !== t2.l && (this.l = [...t2.l]), this.elementProperties = new Map(t2.elementProperties);
  }
  static finalize() {
    if (this.hasOwnProperty(d$1("finalized"))) return;
    if (this.finalized = true, this._$Ei(), this.hasOwnProperty(d$1("properties"))) {
      const t3 = this.properties, s2 = [...r$3(t3), ...o$3(t3)];
      for (const i2 of s2) this.createProperty(i2, t3[i2]);
    }
    const t2 = this[Symbol.metadata];
    if (null !== t2) {
      const s2 = litPropertyMetadata.get(t2);
      if (void 0 !== s2) for (const [t3, i2] of s2) this.elementProperties.set(t3, i2);
    }
    this._$Eh = /* @__PURE__ */ new Map();
    for (const [t3, s2] of this.elementProperties) {
      const i2 = this._$Eu(t3, s2);
      void 0 !== i2 && this._$Eh.set(i2, t3);
    }
    this.elementStyles = this.finalizeStyles(this.styles);
  }
  static finalizeStyles(s2) {
    const i2 = [];
    if (Array.isArray(s2)) {
      const e2 = new Set(s2.flat(1 / 0).reverse());
      for (const s3 of e2) i2.unshift(c$2(s3));
    } else void 0 !== s2 && i2.push(c$2(s2));
    return i2;
  }
  static _$Eu(t2, s2) {
    const i2 = s2.attribute;
    return false === i2 ? void 0 : "string" == typeof i2 ? i2 : "string" == typeof t2 ? t2.toLowerCase() : void 0;
  }
  constructor() {
    super(), this._$Ep = void 0, this.isUpdatePending = false, this.hasUpdated = false, this._$Em = null, this._$Ev();
  }
  _$Ev() {
    var _a2;
    this._$ES = new Promise((t2) => this.enableUpdating = t2), this._$AL = /* @__PURE__ */ new Map(), this._$E_(), this.requestUpdate(), (_a2 = this.constructor.l) == null ? void 0 : _a2.forEach((t2) => t2(this));
  }
  addController(t2) {
    var _a2;
    (this._$EO ?? (this._$EO = /* @__PURE__ */ new Set())).add(t2), void 0 !== this.renderRoot && this.isConnected && ((_a2 = t2.hostConnected) == null ? void 0 : _a2.call(t2));
  }
  removeController(t2) {
    var _a2;
    (_a2 = this._$EO) == null ? void 0 : _a2.delete(t2);
  }
  _$E_() {
    const t2 = /* @__PURE__ */ new Map(), s2 = this.constructor.elementProperties;
    for (const i2 of s2.keys()) this.hasOwnProperty(i2) && (t2.set(i2, this[i2]), delete this[i2]);
    t2.size > 0 && (this._$Ep = t2);
  }
  createRenderRoot() {
    const t2 = this.shadowRoot ?? this.attachShadow(this.constructor.shadowRootOptions);
    return S$1(t2, this.constructor.elementStyles), t2;
  }
  connectedCallback() {
    var _a2;
    this.renderRoot ?? (this.renderRoot = this.createRenderRoot()), this.enableUpdating(true), (_a2 = this._$EO) == null ? void 0 : _a2.forEach((t2) => {
      var _a3;
      return (_a3 = t2.hostConnected) == null ? void 0 : _a3.call(t2);
    });
  }
  enableUpdating(t2) {
  }
  disconnectedCallback() {
    var _a2;
    (_a2 = this._$EO) == null ? void 0 : _a2.forEach((t2) => {
      var _a3;
      return (_a3 = t2.hostDisconnected) == null ? void 0 : _a3.call(t2);
    });
  }
  attributeChangedCallback(t2, s2, i2) {
    this._$AK(t2, i2);
  }
  _$ET(t2, s2) {
    var _a2;
    const i2 = this.constructor.elementProperties.get(t2), e2 = this.constructor._$Eu(t2, i2);
    if (void 0 !== e2 && true === i2.reflect) {
      const h2 = (void 0 !== ((_a2 = i2.converter) == null ? void 0 : _a2.toAttribute) ? i2.converter : u$1).toAttribute(s2, i2.type);
      this._$Em = t2, null == h2 ? this.removeAttribute(e2) : this.setAttribute(e2, h2), this._$Em = null;
    }
  }
  _$AK(t2, s2) {
    var _a2, _b;
    const i2 = this.constructor, e2 = i2._$Eh.get(t2);
    if (void 0 !== e2 && this._$Em !== e2) {
      const t3 = i2.getPropertyOptions(e2), h2 = "function" == typeof t3.converter ? { fromAttribute: t3.converter } : void 0 !== ((_a2 = t3.converter) == null ? void 0 : _a2.fromAttribute) ? t3.converter : u$1;
      this._$Em = e2;
      const r2 = h2.fromAttribute(s2, t3.type);
      this[e2] = r2 ?? ((_b = this._$Ej) == null ? void 0 : _b.get(e2)) ?? r2, this._$Em = null;
    }
  }
  requestUpdate(t2, s2, i2, e2 = false, h2) {
    var _a2;
    if (void 0 !== t2) {
      const r2 = this.constructor;
      if (false === e2 && (h2 = this[t2]), i2 ?? (i2 = r2.getPropertyOptions(t2)), !((i2.hasChanged ?? f$1)(h2, s2) || i2.useDefault && i2.reflect && h2 === ((_a2 = this._$Ej) == null ? void 0 : _a2.get(t2)) && !this.hasAttribute(r2._$Eu(t2, i2)))) return;
      this.C(t2, s2, i2);
    }
    false === this.isUpdatePending && (this._$ES = this._$EP());
  }
  C(t2, s2, { useDefault: i2, reflect: e2, wrapped: h2 }, r2) {
    i2 && !(this._$Ej ?? (this._$Ej = /* @__PURE__ */ new Map())).has(t2) && (this._$Ej.set(t2, r2 ?? s2 ?? this[t2]), true !== h2 || void 0 !== r2) || (this._$AL.has(t2) || (this.hasUpdated || i2 || (s2 = void 0), this._$AL.set(t2, s2)), true === e2 && this._$Em !== t2 && (this._$Eq ?? (this._$Eq = /* @__PURE__ */ new Set())).add(t2));
  }
  async _$EP() {
    this.isUpdatePending = true;
    try {
      await this._$ES;
    } catch (t3) {
      Promise.reject(t3);
    }
    const t2 = this.scheduleUpdate();
    return null != t2 && await t2, !this.isUpdatePending;
  }
  scheduleUpdate() {
    return this.performUpdate();
  }
  performUpdate() {
    var _a2;
    if (!this.isUpdatePending) return;
    if (!this.hasUpdated) {
      if (this.renderRoot ?? (this.renderRoot = this.createRenderRoot()), this._$Ep) {
        for (const [t4, s3] of this._$Ep) this[t4] = s3;
        this._$Ep = void 0;
      }
      const t3 = this.constructor.elementProperties;
      if (t3.size > 0) for (const [s3, i2] of t3) {
        const { wrapped: t4 } = i2, e2 = this[s3];
        true !== t4 || this._$AL.has(s3) || void 0 === e2 || this.C(s3, void 0, i2, e2);
      }
    }
    let t2 = false;
    const s2 = this._$AL;
    try {
      t2 = this.shouldUpdate(s2), t2 ? (this.willUpdate(s2), (_a2 = this._$EO) == null ? void 0 : _a2.forEach((t3) => {
        var _a3;
        return (_a3 = t3.hostUpdate) == null ? void 0 : _a3.call(t3);
      }), this.update(s2)) : this._$EM();
    } catch (s3) {
      throw t2 = false, this._$EM(), s3;
    }
    t2 && this._$AE(s2);
  }
  willUpdate(t2) {
  }
  _$AE(t2) {
    var _a2;
    (_a2 = this._$EO) == null ? void 0 : _a2.forEach((t3) => {
      var _a3;
      return (_a3 = t3.hostUpdated) == null ? void 0 : _a3.call(t3);
    }), this.hasUpdated || (this.hasUpdated = true, this.firstUpdated(t2)), this.updated(t2);
  }
  _$EM() {
    this._$AL = /* @__PURE__ */ new Map(), this.isUpdatePending = false;
  }
  get updateComplete() {
    return this.getUpdateComplete();
  }
  getUpdateComplete() {
    return this._$ES;
  }
  shouldUpdate(t2) {
    return true;
  }
  update(t2) {
    this._$Eq && (this._$Eq = this._$Eq.forEach((t3) => this._$ET(t3, this[t3]))), this._$EM();
  }
  updated(t2) {
  }
  firstUpdated(t2) {
  }
};
y$1.elementStyles = [], y$1.shadowRootOptions = { mode: "open" }, y$1[d$1("elementProperties")] = /* @__PURE__ */ new Map(), y$1[d$1("finalized")] = /* @__PURE__ */ new Map(), p$1 == null ? void 0 : p$1({ ReactiveElement: y$1 }), (a$1.reactiveElementVersions ?? (a$1.reactiveElementVersions = [])).push("2.1.2");
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
const t = globalThis, i$1 = (t2) => t2, s$1 = t.trustedTypes, e = s$1 ? s$1.createPolicy("lit-html", { createHTML: (t2) => t2 }) : void 0, h = "$lit$", o$2 = `lit$${Math.random().toFixed(9).slice(2)}$`, n$1 = "?" + o$2, r$2 = `<${n$1}>`, l = document, c = () => l.createComment(""), a = (t2) => null === t2 || "object" != typeof t2 && "function" != typeof t2, u = Array.isArray, d = (t2) => u(t2) || "function" == typeof (t2 == null ? void 0 : t2[Symbol.iterator]), f = "[ 	\n\f\r]", v = /<(?:(!--|\/[^a-zA-Z])|(\/?[a-zA-Z][^>\s]*)|(\/?$))/g, _ = /-->/g, m = />/g, p = RegExp(`>|${f}(?:([^\\s"'>=/]+)(${f}*=${f}*(?:[^ 	
\f\r"'\`<>=]|("|')|))|$)`, "g"), g = /'/g, $ = /"/g, y2 = /^(?:script|style|textarea|title)$/i, x = (t2) => (i2, ...s2) => ({ _$litType$: t2, strings: i2, values: s2 }), b = x(1), E = Symbol.for("lit-noChange"), A = Symbol.for("lit-nothing"), C = /* @__PURE__ */ new WeakMap(), P = l.createTreeWalker(l, 129);
function V(t2, i2) {
  if (!u(t2) || !t2.hasOwnProperty("raw")) throw Error("invalid template strings array");
  return void 0 !== e ? e.createHTML(i2) : i2;
}
const N = (t2, i2) => {
  const s2 = t2.length - 1, e2 = [];
  let n3, l2 = 2 === i2 ? "<svg>" : 3 === i2 ? "<math>" : "", c2 = v;
  for (let i3 = 0; i3 < s2; i3++) {
    const s3 = t2[i3];
    let a2, u2, d2 = -1, f2 = 0;
    for (; f2 < s3.length && (c2.lastIndex = f2, u2 = c2.exec(s3), null !== u2); ) f2 = c2.lastIndex, c2 === v ? "!--" === u2[1] ? c2 = _ : void 0 !== u2[1] ? c2 = m : void 0 !== u2[2] ? (y2.test(u2[2]) && (n3 = RegExp("</" + u2[2], "g")), c2 = p) : void 0 !== u2[3] && (c2 = p) : c2 === p ? ">" === u2[0] ? (c2 = n3 ?? v, d2 = -1) : void 0 === u2[1] ? d2 = -2 : (d2 = c2.lastIndex - u2[2].length, a2 = u2[1], c2 = void 0 === u2[3] ? p : '"' === u2[3] ? $ : g) : c2 === $ || c2 === g ? c2 = p : c2 === _ || c2 === m ? c2 = v : (c2 = p, n3 = void 0);
    const x2 = c2 === p && t2[i3 + 1].startsWith("/>") ? " " : "";
    l2 += c2 === v ? s3 + r$2 : d2 >= 0 ? (e2.push(a2), s3.slice(0, d2) + h + s3.slice(d2) + o$2 + x2) : s3 + o$2 + (-2 === d2 ? i3 : x2);
  }
  return [V(t2, l2 + (t2[s2] || "<?>") + (2 === i2 ? "</svg>" : 3 === i2 ? "</math>" : "")), e2];
};
class S {
  constructor({ strings: t2, _$litType$: i2 }, e2) {
    let r2;
    this.parts = [];
    let l2 = 0, a2 = 0;
    const u2 = t2.length - 1, d2 = this.parts, [f2, v2] = N(t2, i2);
    if (this.el = S.createElement(f2, e2), P.currentNode = this.el.content, 2 === i2 || 3 === i2) {
      const t3 = this.el.content.firstChild;
      t3.replaceWith(...t3.childNodes);
    }
    for (; null !== (r2 = P.nextNode()) && d2.length < u2; ) {
      if (1 === r2.nodeType) {
        if (r2.hasAttributes()) for (const t3 of r2.getAttributeNames()) if (t3.endsWith(h)) {
          const i3 = v2[a2++], s2 = r2.getAttribute(t3).split(o$2), e3 = /([.?@])?(.*)/.exec(i3);
          d2.push({ type: 1, index: l2, name: e3[2], strings: s2, ctor: "." === e3[1] ? I : "?" === e3[1] ? L : "@" === e3[1] ? z : H }), r2.removeAttribute(t3);
        } else t3.startsWith(o$2) && (d2.push({ type: 6, index: l2 }), r2.removeAttribute(t3));
        if (y2.test(r2.tagName)) {
          const t3 = r2.textContent.split(o$2), i3 = t3.length - 1;
          if (i3 > 0) {
            r2.textContent = s$1 ? s$1.emptyScript : "";
            for (let s2 = 0; s2 < i3; s2++) r2.append(t3[s2], c()), P.nextNode(), d2.push({ type: 2, index: ++l2 });
            r2.append(t3[i3], c());
          }
        }
      } else if (8 === r2.nodeType) if (r2.data === n$1) d2.push({ type: 2, index: l2 });
      else {
        let t3 = -1;
        for (; -1 !== (t3 = r2.data.indexOf(o$2, t3 + 1)); ) d2.push({ type: 7, index: l2 }), t3 += o$2.length - 1;
      }
      l2++;
    }
  }
  static createElement(t2, i2) {
    const s2 = l.createElement("template");
    return s2.innerHTML = t2, s2;
  }
}
function M(t2, i2, s2 = t2, e2) {
  var _a2, _b;
  if (i2 === E) return i2;
  let h2 = void 0 !== e2 ? (_a2 = s2._$Co) == null ? void 0 : _a2[e2] : s2._$Cl;
  const o2 = a(i2) ? void 0 : i2._$litDirective$;
  return (h2 == null ? void 0 : h2.constructor) !== o2 && ((_b = h2 == null ? void 0 : h2._$AO) == null ? void 0 : _b.call(h2, false), void 0 === o2 ? h2 = void 0 : (h2 = new o2(t2), h2._$AT(t2, s2, e2)), void 0 !== e2 ? (s2._$Co ?? (s2._$Co = []))[e2] = h2 : s2._$Cl = h2), void 0 !== h2 && (i2 = M(t2, h2._$AS(t2, i2.values), h2, e2)), i2;
}
class R {
  constructor(t2, i2) {
    this._$AV = [], this._$AN = void 0, this._$AD = t2, this._$AM = i2;
  }
  get parentNode() {
    return this._$AM.parentNode;
  }
  get _$AU() {
    return this._$AM._$AU;
  }
  u(t2) {
    const { el: { content: i2 }, parts: s2 } = this._$AD, e2 = ((t2 == null ? void 0 : t2.creationScope) ?? l).importNode(i2, true);
    P.currentNode = e2;
    let h2 = P.nextNode(), o2 = 0, n3 = 0, r2 = s2[0];
    for (; void 0 !== r2; ) {
      if (o2 === r2.index) {
        let i3;
        2 === r2.type ? i3 = new k(h2, h2.nextSibling, this, t2) : 1 === r2.type ? i3 = new r2.ctor(h2, r2.name, r2.strings, this, t2) : 6 === r2.type && (i3 = new Z(h2, this, t2)), this._$AV.push(i3), r2 = s2[++n3];
      }
      o2 !== (r2 == null ? void 0 : r2.index) && (h2 = P.nextNode(), o2++);
    }
    return P.currentNode = l, e2;
  }
  p(t2) {
    let i2 = 0;
    for (const s2 of this._$AV) void 0 !== s2 && (void 0 !== s2.strings ? (s2._$AI(t2, s2, i2), i2 += s2.strings.length - 2) : s2._$AI(t2[i2])), i2++;
  }
}
class k {
  get _$AU() {
    var _a2;
    return ((_a2 = this._$AM) == null ? void 0 : _a2._$AU) ?? this._$Cv;
  }
  constructor(t2, i2, s2, e2) {
    this.type = 2, this._$AH = A, this._$AN = void 0, this._$AA = t2, this._$AB = i2, this._$AM = s2, this.options = e2, this._$Cv = (e2 == null ? void 0 : e2.isConnected) ?? true;
  }
  get parentNode() {
    let t2 = this._$AA.parentNode;
    const i2 = this._$AM;
    return void 0 !== i2 && 11 === (t2 == null ? void 0 : t2.nodeType) && (t2 = i2.parentNode), t2;
  }
  get startNode() {
    return this._$AA;
  }
  get endNode() {
    return this._$AB;
  }
  _$AI(t2, i2 = this) {
    t2 = M(this, t2, i2), a(t2) ? t2 === A || null == t2 || "" === t2 ? (this._$AH !== A && this._$AR(), this._$AH = A) : t2 !== this._$AH && t2 !== E && this._(t2) : void 0 !== t2._$litType$ ? this.$(t2) : void 0 !== t2.nodeType ? this.T(t2) : d(t2) ? this.k(t2) : this._(t2);
  }
  O(t2) {
    return this._$AA.parentNode.insertBefore(t2, this._$AB);
  }
  T(t2) {
    this._$AH !== t2 && (this._$AR(), this._$AH = this.O(t2));
  }
  _(t2) {
    this._$AH !== A && a(this._$AH) ? this._$AA.nextSibling.data = t2 : this.T(l.createTextNode(t2)), this._$AH = t2;
  }
  $(t2) {
    var _a2;
    const { values: i2, _$litType$: s2 } = t2, e2 = "number" == typeof s2 ? this._$AC(t2) : (void 0 === s2.el && (s2.el = S.createElement(V(s2.h, s2.h[0]), this.options)), s2);
    if (((_a2 = this._$AH) == null ? void 0 : _a2._$AD) === e2) this._$AH.p(i2);
    else {
      const t3 = new R(e2, this), s3 = t3.u(this.options);
      t3.p(i2), this.T(s3), this._$AH = t3;
    }
  }
  _$AC(t2) {
    let i2 = C.get(t2.strings);
    return void 0 === i2 && C.set(t2.strings, i2 = new S(t2)), i2;
  }
  k(t2) {
    u(this._$AH) || (this._$AH = [], this._$AR());
    const i2 = this._$AH;
    let s2, e2 = 0;
    for (const h2 of t2) e2 === i2.length ? i2.push(s2 = new k(this.O(c()), this.O(c()), this, this.options)) : s2 = i2[e2], s2._$AI(h2), e2++;
    e2 < i2.length && (this._$AR(s2 && s2._$AB.nextSibling, e2), i2.length = e2);
  }
  _$AR(t2 = this._$AA.nextSibling, s2) {
    var _a2;
    for ((_a2 = this._$AP) == null ? void 0 : _a2.call(this, false, true, s2); t2 !== this._$AB; ) {
      const s3 = i$1(t2).nextSibling;
      i$1(t2).remove(), t2 = s3;
    }
  }
  setConnected(t2) {
    var _a2;
    void 0 === this._$AM && (this._$Cv = t2, (_a2 = this._$AP) == null ? void 0 : _a2.call(this, t2));
  }
}
class H {
  get tagName() {
    return this.element.tagName;
  }
  get _$AU() {
    return this._$AM._$AU;
  }
  constructor(t2, i2, s2, e2, h2) {
    this.type = 1, this._$AH = A, this._$AN = void 0, this.element = t2, this.name = i2, this._$AM = e2, this.options = h2, s2.length > 2 || "" !== s2[0] || "" !== s2[1] ? (this._$AH = Array(s2.length - 1).fill(new String()), this.strings = s2) : this._$AH = A;
  }
  _$AI(t2, i2 = this, s2, e2) {
    const h2 = this.strings;
    let o2 = false;
    if (void 0 === h2) t2 = M(this, t2, i2, 0), o2 = !a(t2) || t2 !== this._$AH && t2 !== E, o2 && (this._$AH = t2);
    else {
      const e3 = t2;
      let n3, r2;
      for (t2 = h2[0], n3 = 0; n3 < h2.length - 1; n3++) r2 = M(this, e3[s2 + n3], i2, n3), r2 === E && (r2 = this._$AH[n3]), o2 || (o2 = !a(r2) || r2 !== this._$AH[n3]), r2 === A ? t2 = A : t2 !== A && (t2 += (r2 ?? "") + h2[n3 + 1]), this._$AH[n3] = r2;
    }
    o2 && !e2 && this.j(t2);
  }
  j(t2) {
    t2 === A ? this.element.removeAttribute(this.name) : this.element.setAttribute(this.name, t2 ?? "");
  }
}
class I extends H {
  constructor() {
    super(...arguments), this.type = 3;
  }
  j(t2) {
    this.element[this.name] = t2 === A ? void 0 : t2;
  }
}
class L extends H {
  constructor() {
    super(...arguments), this.type = 4;
  }
  j(t2) {
    this.element.toggleAttribute(this.name, !!t2 && t2 !== A);
  }
}
class z extends H {
  constructor(t2, i2, s2, e2, h2) {
    super(t2, i2, s2, e2, h2), this.type = 5;
  }
  _$AI(t2, i2 = this) {
    if ((t2 = M(this, t2, i2, 0) ?? A) === E) return;
    const s2 = this._$AH, e2 = t2 === A && s2 !== A || t2.capture !== s2.capture || t2.once !== s2.once || t2.passive !== s2.passive, h2 = t2 !== A && (s2 === A || e2);
    e2 && this.element.removeEventListener(this.name, this, s2), h2 && this.element.addEventListener(this.name, this, t2), this._$AH = t2;
  }
  handleEvent(t2) {
    var _a2;
    "function" == typeof this._$AH ? this._$AH.call(((_a2 = this.options) == null ? void 0 : _a2.host) ?? this.element, t2) : this._$AH.handleEvent(t2);
  }
}
class Z {
  constructor(t2, i2, s2) {
    this.element = t2, this.type = 6, this._$AN = void 0, this._$AM = i2, this.options = s2;
  }
  get _$AU() {
    return this._$AM._$AU;
  }
  _$AI(t2) {
    M(this, t2);
  }
}
const B = t.litHtmlPolyfillSupport;
B == null ? void 0 : B(S, k), (t.litHtmlVersions ?? (t.litHtmlVersions = [])).push("3.3.3");
const D = (t2, i2, s2) => {
  const e2 = (s2 == null ? void 0 : s2.renderBefore) ?? i2;
  let h2 = e2._$litPart$;
  if (void 0 === h2) {
    const t3 = (s2 == null ? void 0 : s2.renderBefore) ?? null;
    e2._$litPart$ = h2 = new k(i2.insertBefore(c(), t3), t3, void 0, s2 ?? {});
  }
  return h2._$AI(t2), h2;
};
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
const s = globalThis;
class i extends y$1 {
  constructor() {
    super(...arguments), this.renderOptions = { host: this }, this._$Do = void 0;
  }
  createRenderRoot() {
    var _a2;
    const t2 = super.createRenderRoot();
    return (_a2 = this.renderOptions).renderBefore ?? (_a2.renderBefore = t2.firstChild), t2;
  }
  update(t2) {
    const r2 = this.render();
    this.hasUpdated || (this.renderOptions.isConnected = this.isConnected), super.update(t2), this._$Do = D(r2, this.renderRoot, this.renderOptions);
  }
  connectedCallback() {
    var _a2;
    super.connectedCallback(), (_a2 = this._$Do) == null ? void 0 : _a2.setConnected(true);
  }
  disconnectedCallback() {
    var _a2;
    super.disconnectedCallback(), (_a2 = this._$Do) == null ? void 0 : _a2.setConnected(false);
  }
  render() {
    return E;
  }
}
i._$litElement$ = true, i["finalized"] = true, (_a = s.litElementHydrateSupport) == null ? void 0 : _a.call(s, { LitElement: i });
const o$1 = s.litElementPolyfillSupport;
o$1 == null ? void 0 : o$1({ LitElement: i });
(s.litElementVersions ?? (s.litElementVersions = [])).push("4.2.2");
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
const o = { attribute: true, type: String, converter: u$1, reflect: false, hasChanged: f$1 }, r$1 = (t2 = o, e2, r2) => {
  const { kind: n3, metadata: i2 } = r2;
  let s2 = globalThis.litPropertyMetadata.get(i2);
  if (void 0 === s2 && globalThis.litPropertyMetadata.set(i2, s2 = /* @__PURE__ */ new Map()), "setter" === n3 && ((t2 = Object.create(t2)).wrapped = true), s2.set(r2.name, t2), "accessor" === n3) {
    const { name: o2 } = r2;
    return { set(r3) {
      const n4 = e2.get.call(this);
      e2.set.call(this, r3), this.requestUpdate(o2, n4, t2, true, r3);
    }, init(e3) {
      return void 0 !== e3 && this.C(o2, void 0, t2, e3), e3;
    } };
  }
  if ("setter" === n3) {
    const { name: o2 } = r2;
    return function(r3) {
      const n4 = this[o2];
      e2.call(this, r3), this.requestUpdate(o2, n4, t2, true, r3);
    };
  }
  throw Error("Unsupported decorator location: " + n3);
};
function n2(t2) {
  return (e2, o2) => "object" == typeof o2 ? r$1(t2, e2, o2) : ((t3, e3, o3) => {
    const r2 = e3.hasOwnProperty(o3);
    return e3.constructor.createProperty(o3, t3), r2 ? Object.getOwnPropertyDescriptor(e3, o3) : void 0;
  })(t2, e2, o2);
}
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
function r(r2) {
  return n2({ ...r2, state: true, attribute: false });
}
const DAYS_OF_WEEK = [
  "monday",
  "tuesday",
  "wednesday",
  "thursday",
  "friday",
  "saturday",
  "sunday"
];
const DAY_LABELS = {
  monday: { short: "Mon", full: "Monday" },
  tuesday: { short: "Tue", full: "Tuesday" },
  wednesday: { short: "Wed", full: "Wednesday" },
  thursday: { short: "Thu", full: "Thursday" },
  friday: { short: "Fri", full: "Friday" },
  saturday: { short: "Sat", full: "Saturday" },
  sunday: { short: "Sun", full: "Sunday" }
};
function timeStringToMinutes(timeStr) {
  if (!timeStr) return 0;
  const parts = timeStr.split(":").map((p2) => parseInt(p2, 10));
  const hours = parts[0] || 0;
  const minutes = parts[1] || 0;
  return Math.min(1440, Math.max(0, hours * 60 + minutes));
}
function minutesToTimeString(minutes) {
  const clamped = Math.min(1440, Math.max(0, Math.round(minutes)));
  const hours = Math.floor(clamped / 60);
  const mins = clamped % 60;
  return `${String(hours).padStart(2, "0")}:${String(mins).padStart(2, "0")}:00`;
}
function formatTimeDisplay(minutes, use24Hour = true) {
  const clamped = Math.min(1440, Math.max(0, Math.round(minutes)));
  const hours = Math.floor(clamped / 60);
  const mins = clamped % 60;
  if (use24Hour) {
    return `${String(hours).padStart(2, "0")}:${String(mins).padStart(2, "0")}`;
  }
  const period = hours >= 12 && hours < 24 ? "PM" : "AM";
  const displayHours = hours % 12 === 0 ? 12 : hours % 12;
  return `${displayHours}:${String(mins).padStart(2, "0")} ${period}`;
}
function snapMinutes(minutes, stepSize = 15) {
  const rounded = Math.round(minutes / stepSize) * stepSize;
  return Math.min(1440, Math.max(0, rounded));
}
let syncChannel = null;
try {
  if (typeof BroadcastChannel !== "undefined") {
    syncChannel = new BroadcastChannel("ha-schedule-sync-bus");
  }
} catch {
}
let activeSubscribers = 0;
let pollTimer = null;
const lastKnownHashes = /* @__PURE__ */ new Map();
let latestHass = null;
async function checkSchedulesForChanges() {
  if (!latestHass) return;
  if (typeof document !== "undefined" && document.hidden) return;
  try {
    const list = await latestHass.callWS({ type: "schedule/list" });
    if (!list) return;
    for (const item of list) {
      const currentHash = JSON.stringify(item);
      const prevHash = lastKnownHashes.get(item.id);
      if (prevHash && prevHash !== currentHash) {
        lastKnownHashes.set(item.id, currentHash);
        notifyScheduleUpdated(item.id);
      } else {
        lastKnownHashes.set(item.id, currentHash);
      }
    }
  } catch {
  }
}
function startPolling() {
  if (pollTimer) return;
  pollTimer = setInterval(checkSchedulesForChanges, 15e3);
}
function stopPolling() {
  if (pollTimer) {
    clearInterval(pollTimer);
    pollTimer = null;
  }
}
if (typeof document !== "undefined") {
  document.addEventListener("visibilitychange", () => {
    if (!document.hidden && activeSubscribers > 0) {
      checkSchedulesForChanges();
    }
  });
}
function notifyScheduleUpdated(scheduleId) {
  if (typeof window !== "undefined") {
    window.dispatchEvent(
      new CustomEvent("ha-schedule-updated", {
        detail: { scheduleId }
      })
    );
  }
  if (syncChannel) {
    try {
      syncChannel.postMessage({ type: "schedule-updated", scheduleId });
    } catch {
    }
  }
}
function subscribeScheduleUpdates(callback) {
  activeSubscribers++;
  startPolling();
  const windowHandler = (e2) => {
    const detail = e2.detail;
    callback(detail == null ? void 0 : detail.scheduleId);
  };
  const channelHandler = (e2) => {
    var _a2, _b;
    if (((_a2 = e2.data) == null ? void 0 : _a2.type) === "schedule-updated") {
      callback((_b = e2.data) == null ? void 0 : _b.scheduleId);
    }
  };
  if (typeof window !== "undefined") {
    window.addEventListener("ha-schedule-updated", windowHandler);
  }
  if (syncChannel) {
    syncChannel.addEventListener("message", channelHandler);
  }
  return () => {
    activeSubscribers = Math.max(0, activeSubscribers - 1);
    if (activeSubscribers === 0) {
      stopPolling();
    }
    if (typeof window !== "undefined") {
      window.removeEventListener("ha-schedule-updated", windowHandler);
    }
    if (syncChannel) {
      syncChannel.removeEventListener("message", channelHandler);
    }
  };
}
async function fetchScheduleList(hass) {
  latestHass = hass;
  try {
    const list = await hass.callWS({ type: "schedule/list" });
    if (list) {
      for (const item of list) {
        lastKnownHashes.set(item.id, JSON.stringify(item));
      }
    }
    return list || [];
  } catch (err) {
    console.warn("[schedule-preset-card] Failed to fetch schedule list via WebSocket:", err);
    return [];
  }
}
async function updateHASchedule(hass, scheduleId, name, days, icon) {
  latestHass = hass;
  const payload = {
    type: "schedule/update",
    schedule_id: scheduleId,
    name,
    ...days
  };
  if (icon) {
    payload.icon = icon;
  }
  await hass.callWS(payload);
  const simulated = { id: scheduleId, name, icon, ...days };
  lastKnownHashes.set(scheduleId, JSON.stringify(simulated));
  notifyScheduleUpdated(scheduleId);
}
function isClimatePayload(data) {
  if (!data || typeof data !== "object") return false;
  return data.hvac_mode !== void 0 || data.mode !== void 0 || data.heat_to !== void 0 || data.cool_to !== void 0 || data.target_temp_low !== void 0 || data.target_temp_high !== void 0 || data.temperature !== void 0;
}
function isForeignSchedule(scheduleItem) {
  if (!scheduleItem) return false;
  let totalBlocks = 0;
  let climateBlocks = 0;
  for (const day of DAYS_OF_WEEK) {
    const rawBlocks = scheduleItem[day] || [];
    totalBlocks += rawBlocks.length;
    for (const b2 of rawBlocks) {
      if (isClimatePayload(b2.data)) {
        climateBlocks++;
      }
    }
  }
  if (totalBlocks === 0) return false;
  return climateBlocks === 0;
}
function findScheduleInList(list, entityId, hass) {
  var _a2;
  if (!list || list.length === 0 || !entityId) return void 0;
  const fullEntityId = entityId.startsWith("schedule.") ? entityId : `schedule.${entityId}`;
  const shortId = entityId.replace(/^schedule\./, "");
  const entities = hass == null ? void 0 : hass.entities;
  if (entities && ((_a2 = entities[fullEntityId]) == null ? void 0 : _a2.unique_id)) {
    const storageId = entities[fullEntityId].unique_id;
    const match = list.find((s2) => s2.id === storageId);
    if (match) return match;
  }
  return list.find((s2) => s2.id === fullEntityId || s2.id === shortId);
}
function convertToInternalBlocks(scheduleItem) {
  const result = {
    monday: [],
    tuesday: [],
    wednesday: [],
    thursday: [],
    friday: [],
    saturday: [],
    sunday: []
  };
  if (!scheduleItem) return result;
  for (const day of DAYS_OF_WEEK) {
    const rawBlocks = scheduleItem[day] || [];
    result[day] = rawBlocks.map((b2, index) => {
      const data = b2.data || {};
      const hasClimate = isClimatePayload(data);
      const mode = (data.hvac_mode || data.mode || (hasClimate ? "heat_cool" : "off")).toLowerCase();
      const heat = data.heat_to ?? data.target_temp_low ?? data.temperature ?? 68;
      const cool = data.cool_to ?? data.target_temp_high ?? 74;
      return {
        id: `${day}_block_${index}_${Date.now()}`,
        day,
        startMinutes: timeStringToMinutes(b2.from),
        endMinutes: timeStringToMinutes(b2.to),
        hvac_mode: ["heat_cool", "heat", "cool", "off"].includes(mode) ? mode : "heat_cool",
        heat_to: Number(heat),
        cool_to: Number(cool),
        isGeneric: !hasClimate,
        originalData: data
      };
    });
  }
  return result;
}
function convertToHABlocks(blocksByDay) {
  const result = {
    monday: [],
    tuesday: [],
    wednesday: [],
    thursday: [],
    friday: [],
    saturday: [],
    sunday: []
  };
  for (const day of DAYS_OF_WEEK) {
    const valid = blocksByDay[day].filter((b2) => b2.endMinutes > b2.startMinutes);
    valid.sort((a2, b2) => a2.startMinutes - b2.startMinutes);
    const sanitized = [];
    for (const b2 of valid) {
      if (sanitized.length > 0) {
        const prev = sanitized[sanitized.length - 1];
        if (prev.endMinutes > b2.startMinutes) {
          prev.endMinutes = b2.startMinutes;
          if (prev.endMinutes <= prev.startMinutes) {
            sanitized.pop();
          }
        }
      }
      if (b2.endMinutes > b2.startMinutes) {
        sanitized.push({ ...b2 });
      }
    }
    result[day] = sanitized.map((block) => {
      const dataPayload = {
        ...block.originalData || {},
        hvac_mode: block.hvac_mode
      };
      if (block.hvac_mode === "heat_cool") {
        dataPayload.heat_to = block.heat_to;
        dataPayload.cool_to = block.cool_to;
      } else if (block.hvac_mode === "heat") {
        dataPayload.heat_to = block.heat_to;
        delete dataPayload.cool_to;
      } else if (block.hvac_mode === "cool") {
        dataPayload.cool_to = block.cool_to;
        delete dataPayload.heat_to;
      } else if (block.hvac_mode === "off") {
        delete dataPayload.heat_to;
        delete dataPayload.cool_to;
      }
      return {
        from: minutesToTimeString(block.startMinutes),
        to: minutesToTimeString(block.endMinutes),
        data: dataPayload
      };
    });
  }
  return result;
}
function clamp(val, min, max) {
  return Math.min(max, Math.max(min, val));
}
function interpolateHsl(h1, s1, l1, h2, s2, l2, t2) {
  const h3 = h1 + (h2 - h1) * t2;
  const s3 = s1 + (s2 - s1) * t2;
  const l3 = l1 + (l2 - l1) * t2;
  return `hsl(${Math.round(h3)}, ${Math.round(s3)}%, ${Math.round(l3)}%)`;
}
function getHeatColor(temp, unit = "°F") {
  const minTemp = unit === "°C" ? 10 : 50;
  const maxTemp = unit === "°C" ? 24 : 75;
  const t2 = clamp((temp - minTemp) / (maxTemp - minTemp), 0, 1);
  return interpolateHsl(34, 90, 86, 0, 82, 48, t2);
}
function getCoolColor(temp, unit = "°F") {
  const minTemp = unit === "°C" ? 18 : 65;
  const maxTemp = unit === "°C" ? 28 : 82;
  const t2 = clamp((maxTemp - temp) / (maxTemp - minTemp), 0, 1);
  return interpolateHsl(204, 85, 90, 202, 92, 38, t2);
}
function getHeatTextColor(temp, unit = "°F") {
  const threshold = unit === "°C" ? 18 : 64;
  return temp >= threshold ? "#ffffff" : "#431407";
}
function getCoolTextColor(temp, unit = "°F") {
  const threshold = unit === "°C" ? 22 : 72;
  return temp <= threshold ? "#ffffff" : "#082f49";
}
function getSplitOrientation(width, height) {
  if (height < 38 || width > height) {
    return "side-by-side";
  }
  return "stacked";
}
var __defProp$4 = Object.defineProperty;
var __decorateClass$4 = (decorators, target, key, kind) => {
  var result = void 0;
  for (var i2 = decorators.length - 1, decorator; i2 >= 0; i2--)
    if (decorator = decorators[i2])
      result = decorator(target, key, result) || result;
  if (result) __defProp$4(target, key, result);
  return result;
};
const _PresetDialog = class _PresetDialog extends i {
  constructor() {
    super(...arguments);
    this.temperatureUnit = "°F";
    this.minDeadband = 2;
    this.minTemp = 45;
    this.maxTemp = 85;
    this.currentMode = "heat_cool";
    this.heatTo = 68;
    this.coolTo = 74;
    this.splitMinute = 720;
  }
  connectedCallback() {
    super.connectedCallback();
    if (this.block) {
      this.currentMode = this.block.hvac_mode || "heat_cool";
      this.heatTo = this.block.heat_to ?? 68;
      this.coolTo = this.block.cool_to ?? 74;
      const dur = this.block.endMinutes - this.block.startMinutes;
      this.splitMinute = Math.min(
        this.block.endMinutes - 15,
        Math.max(this.block.startMinutes + 15, Math.round((this.block.startMinutes + dur / 2) / 15) * 15)
      );
    }
  }
  stepSplit(deltaMinutes) {
    const next = this.splitMinute + deltaMinutes;
    if (next <= this.block.startMinutes || next >= this.block.endMinutes) return;
    this.splitMinute = next;
  }
  handleSplit() {
    this.dispatchEvent(
      new CustomEvent("split-block", {
        detail: {
          blockId: this.block.id,
          day: this.block.day,
          splitMinute: this.splitMinute
        },
        bubbles: true,
        composed: true
      })
    );
  }
  handleSetMode(mode) {
    this.currentMode = mode;
  }
  stepHeat(delta) {
    const next = this.heatTo + delta;
    if (next < this.minTemp) return;
    if (this.currentMode === "heat_cool" && next > this.coolTo - this.minDeadband) {
      return;
    }
    this.heatTo = next;
  }
  stepCool(delta) {
    const next = this.coolTo + delta;
    if (next > this.maxTemp) return;
    if (this.currentMode === "heat_cool" && next < this.heatTo + this.minDeadband) {
      return;
    }
    this.coolTo = next;
  }
  handleSave() {
    this.dispatchEvent(
      new CustomEvent("save-block", {
        detail: {
          block: {
            ...this.block,
            hvac_mode: this.currentMode,
            heat_to: this.heatTo,
            cool_to: this.coolTo
          }
        },
        bubbles: true,
        composed: true
      })
    );
  }
  handleDelete() {
    this.dispatchEvent(
      new CustomEvent("delete-block", {
        detail: { blockId: this.block.id, day: this.block.day },
        bubbles: true,
        composed: true
      })
    );
  }
  handleCopyTo(target) {
    this.dispatchEvent(
      new CustomEvent("copy-block-to", {
        detail: {
          block: {
            ...this.block,
            hvac_mode: this.currentMode,
            heat_to: this.heatTo,
            cool_to: this.coolTo
          },
          target
        },
        bubbles: true,
        composed: true
      })
    );
  }
  handleClose() {
    this.dispatchEvent(new CustomEvent("close-dialog", { bubbles: true, composed: true }));
  }
  render() {
    var _a2;
    if (!this.block) return b``;
    const dayName = ((_a2 = DAY_LABELS[this.block.day]) == null ? void 0 : _a2.full) || this.block.day;
    const timeRange = `${formatTimeDisplay(this.block.startMinutes)} – ${formatTimeDisplay(this.block.endMinutes)}`;
    const heatColor = getHeatColor(this.heatTo, this.temperatureUnit);
    const heatText = getHeatTextColor(this.heatTo, this.temperatureUnit);
    const coolColor = getCoolColor(this.coolTo, this.temperatureUnit);
    const coolText = getCoolTextColor(this.coolTo, this.temperatureUnit);
    return b`
      <div class="modal-backdrop" @click=${(e2) => e2.target === e2.currentTarget && this.handleClose()}>
        <div class="dialog-card">
          <div class="dialog-header">
            <div>
              <h3 class="dialog-title">${dayName} Preset</h3>
              <div class="dialog-subtitle">${timeRange}</div>
            </div>
            <button class="close-btn" @click=${this.handleClose}>&times;</button>
          </div>

          <div class="dialog-body">
            <!-- Mode Selector -->
            <div class="mode-selector">
              <button
                class="mode-btn ${this.currentMode === "heat_cool" ? "active" : ""}"
                @click=${() => this.handleSetMode("heat_cool")}
              >
                <span>Dual</span>
                <span>Auto</span>
              </button>
              <button
                class="mode-btn ${this.currentMode === "heat" ? "active" : ""}"
                @click=${() => this.handleSetMode("heat")}
              >
                <span>🔥</span>
                <span>Heat</span>
              </button>
              <button
                class="mode-btn ${this.currentMode === "cool" ? "active" : ""}"
                @click=${() => this.handleSetMode("cool")}
              >
                <span>❄️</span>
                <span>Cool</span>
              </button>
              <button
                class="mode-btn ${this.currentMode === "off" ? "active" : ""}"
                @click=${() => this.handleSetMode("off")}
              >
                <span>⭕</span>
                <span>Off</span>
              </button>
            </div>

            <!-- Setpoint Steppers -->
            <div class="setpoint-section">
              ${this.currentMode === "heat_cool" || this.currentMode === "cool" ? b`
                    <div class="stepper-row">
                      <div class="stepper-label">
                        <div class="stepper-name">
                          <span>❄️</span> Cool To
                        </div>
                      </div>
                      <div class="stepper-controls">
                        <button
                          class="step-btn"
                          @click=${() => this.stepCool(-1)}
                          ?disabled=${this.coolTo <= (this.currentMode === "heat_cool" ? this.heatTo + this.minDeadband : this.minTemp)}
                        >-</button>
                        <div
                          class="stepper-badge"
                          style="background-color: ${coolColor}; color: ${coolText};"
                        >
                          ${this.coolTo}°
                        </div>
                        <button
                          class="step-btn"
                          @click=${() => this.stepCool(1)}
                          ?disabled=${this.coolTo >= this.maxTemp}
                        >+</button>
                      </div>
                    </div>
                  ` : ""}

              ${this.currentMode === "heat_cool" || this.currentMode === "heat" ? b`
                    <div class="stepper-row">
                      <div class="stepper-label">
                        <div class="stepper-name">
                          <span>🔥</span> Heat To
                        </div>
                      </div>
                      <div class="stepper-controls">
                        <button
                          class="step-btn"
                          @click=${() => this.stepHeat(-1)}
                          ?disabled=${this.heatTo <= this.minTemp}
                        >-</button>
                        <div
                          class="stepper-badge"
                          style="background-color: ${heatColor}; color: ${heatText};"
                        >
                          ${this.heatTo}°
                        </div>
                        <button
                          class="step-btn"
                          @click=${() => this.stepHeat(1)}
                          ?disabled=${this.heatTo >= (this.currentMode === "heat_cool" ? this.coolTo - this.minDeadband : this.maxTemp)}
                        >+</button>
                      </div>
                    </div>
                  ` : ""}

              ${this.currentMode === "off" ? b`
                    <div style="text-align: center; color: var(--secondary-text-color, #9ca3af); font-size: 0.9rem; padding: 12px;">
                      Zone will be turned OFF during this time interval.
                    </div>
                  ` : ""}
            </div>

            <!-- Split Section -->
            ${this.block.endMinutes - this.block.startMinutes >= 30 ? b`
                  <div class="split-section">
                    <div class="split-header">✂️ Split Block at Time</div>
                    <div class="split-controls">
                      <button
                        class="step-btn"
                        style="width: 32px; height: 32px; font-size: 1rem;"
                        @click=${() => this.stepSplit(-15)}
                        ?disabled=${this.splitMinute <= this.block.startMinutes + 15}
                      >-</button>
                      <div class="split-badge">${formatTimeDisplay(this.splitMinute)}</div>
                      <button
                        class="step-btn"
                        style="width: 32px; height: 32px; font-size: 1rem;"
                        @click=${() => this.stepSplit(15)}
                        ?disabled=${this.splitMinute >= this.block.endMinutes - 15}
                      >+</button>
                      <button class="split-action-btn" @click=${this.handleSplit}>
                        Split into Two
                      </button>
                    </div>
                  </div>
                ` : ""}

            <!-- Quick Copy Shortcuts -->
            <div style="font-size: 0.8rem; font-weight: 500; color: var(--secondary-text-color, #9ca3af);">
              Quick Copy:
            </div>
            <div class="shortcuts-section">
              <button class="shortcut-btn" @click=${() => this.handleCopyTo("weekdays")}>
                Copy to Weekdays
              </button>
              <button class="shortcut-btn" @click=${() => this.handleCopyTo("weekend")}>
                Copy to Weekend
              </button>
              <button class="shortcut-btn" @click=${() => this.handleCopyTo("all")}>
                Copy to All 7 Days
              </button>
            </div>
          </div>

          <div class="dialog-footer">
            <button class="delete-btn" @click=${this.handleDelete}>Delete Block</button>
            <button class="save-btn" @click=${this.handleSave}>Apply</button>
          </div>
        </div>
      </div>
    `;
  }
};
_PresetDialog.styles = i$3`
    :host {
      display: block;
    }

    .modal-backdrop {
      position: fixed;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      background: rgba(0, 0, 0, 0.65);
      backdrop-filter: blur(4px);
      z-index: 999;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 16px;
      box-sizing: border-box;
    }

    .dialog-card {
      background: var(--card-background-color, #1f2937);
      color: var(--primary-text-color, #f3f4f6);
      border-radius: 16px;
      border: 1px solid var(--divider-color, rgba(255, 255, 255, 0.1));
      width: 100%;
      max-width: 440px;
      box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.5), 0 8px 10px -6px rgba(0, 0, 0, 0.5);
      overflow: hidden;
      animation: popIn 0.18s ease-out;
    }

    @keyframes popIn {
      from {
        opacity: 0;
        transform: scale(0.95);
      }
      to {
        opacity: 1;
        transform: scale(1);
      }
    }

    .dialog-header {
      padding: 16px 20px;
      border-bottom: 1px solid var(--divider-color, rgba(255, 255, 255, 0.08));
      display: flex;
      justify-content: space-between;
      align-items: center;
    }

    .dialog-title {
      font-size: 1.15rem;
      font-weight: 600;
      margin: 0;
    }

    .dialog-subtitle {
      font-size: 0.85rem;
      color: var(--secondary-text-color, #9ca3af);
      margin-top: 2px;
    }

    .close-btn {
      background: transparent;
      border: none;
      color: var(--secondary-text-color, #9ca3af);
      font-size: 1.5rem;
      cursor: pointer;
      line-height: 1;
      padding: 4px;
      border-radius: 6px;
    }
    .close-btn:hover {
      color: #fff;
      background: rgba(255, 255, 255, 0.08);
    }

    .dialog-body {
      padding: 20px;
      display: flex;
      flex-direction: column;
      gap: 20px;
    }

    /* Mode selector */
    .mode-selector {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 6px;
      background: rgba(0, 0, 0, 0.25);
      padding: 4px;
      border-radius: 10px;
    }

    .mode-btn {
      padding: 8px 6px;
      font-size: 0.82rem;
      font-weight: 500;
      border-radius: 8px;
      border: none;
      cursor: pointer;
      background: transparent;
      color: var(--secondary-text-color, #9ca3af);
      transition: all 0.15s ease;
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 4px;
    }

    .mode-btn:hover {
      color: #fff;
    }

    .mode-btn.active {
      background: var(--primary-color, #3b82f6);
      color: #ffffff;
      font-weight: 600;
      box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
    }

    /* Temperature controls */
    .setpoint-section {
      display: flex;
      flex-direction: column;
      gap: 14px;
    }

    .stepper-row {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 12px 16px;
      border-radius: 12px;
      background: rgba(255, 255, 255, 0.04);
      border: 1px solid rgba(255, 255, 255, 0.06);
    }

    .stepper-label {
      display: flex;
      flex-direction: column;
      gap: 2px;
    }

    .stepper-name {
      font-size: 0.9rem;
      font-weight: 500;
      display: flex;
      align-items: center;
      gap: 6px;
    }

    .stepper-badge {
      font-size: 1.3rem;
      font-weight: 700;
      padding: 4px 10px;
      border-radius: 8px;
      min-width: 55px;
      text-align: center;
    }

    .stepper-controls {
      display: flex;
      align-items: center;
      gap: 10px;
    }

    .step-btn {
      width: 36px;
      height: 36px;
      border-radius: 50%;
      border: 1px solid rgba(255, 255, 255, 0.15);
      background: rgba(255, 255, 255, 0.08);
      color: #fff;
      font-size: 1.2rem;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      transition: background 0.15s;
    }
    .step-btn:hover:not(:disabled) {
      background: rgba(255, 255, 255, 0.2);
    }
    .step-btn:disabled {
      opacity: 0.3;
      cursor: not-allowed;
    }

    /* Split block section */
    .split-section {
      display: flex;
      flex-direction: column;
      gap: 8px;
      padding: 12px 14px;
      border-radius: 10px;
      background: rgba(255, 255, 255, 0.03);
      border: 1px dashed rgba(255, 255, 255, 0.12);
    }

    .split-header {
      font-size: 0.82rem;
      font-weight: 500;
      color: var(--secondary-text-color, #9ca3af);
    }

    .split-controls {
      display: flex;
      align-items: center;
      gap: 10px;
    }

    .split-badge {
      font-size: 0.95rem;
      font-weight: 600;
      padding: 4px 10px;
      border-radius: 6px;
      background: rgba(255, 255, 255, 0.08);
      color: #fff;
    }

    .split-action-btn {
      margin-left: auto;
      padding: 6px 12px;
      font-size: 0.8rem;
      font-weight: 600;
      border-radius: 6px;
      border: 1px solid var(--primary-color, #38bdf8);
      background: rgba(56, 189, 248, 0.15);
      color: var(--primary-color, #38bdf8);
      cursor: pointer;
      transition: all 0.15s;
    }
    .split-action-btn:hover {
      background: var(--primary-color, #38bdf8);
      color: #fff;
    }

    /* Copy shortcuts */
    .shortcuts-section {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }

    .shortcut-btn {
      flex: 1;
      min-width: 100px;
      padding: 7px 10px;
      font-size: 0.78rem;
      border-radius: 8px;
      background: rgba(255, 255, 255, 0.05);
      border: 1px solid rgba(255, 255, 255, 0.1);
      color: var(--secondary-text-color, #9ca3af);
      cursor: pointer;
      text-align: center;
      transition: background 0.15s;
    }
    .shortcut-btn:hover {
      background: rgba(255, 255, 255, 0.12);
      color: #fff;
    }

    /* Dialog footer */
    .dialog-footer {
      padding: 16px 20px;
      border-top: 1px solid var(--divider-color, rgba(255, 255, 255, 0.08));
      display: flex;
      justify-content: space-between;
      align-items: center;
      background: rgba(0, 0, 0, 0.15);
    }

    .delete-btn {
      background: transparent;
      border: 1px solid #ef4444;
      color: #ef4444;
      padding: 8px 14px;
      border-radius: 8px;
      font-size: 0.85rem;
      font-weight: 500;
      cursor: pointer;
      transition: all 0.15s;
    }
    .delete-btn:hover {
      background: #ef4444;
      color: #fff;
    }

    .save-btn {
      background: var(--primary-color, #3b82f6);
      border: none;
      color: #fff;
      padding: 9px 20px;
      border-radius: 8px;
      font-size: 0.9rem;
      font-weight: 600;
      cursor: pointer;
      transition: opacity 0.15s;
    }
    .save-btn:hover {
      opacity: 0.9;
    }
  `;
let PresetDialog = _PresetDialog;
__decorateClass$4([
  n2({ type: Object })
], PresetDialog.prototype, "block");
__decorateClass$4([
  n2({ type: String })
], PresetDialog.prototype, "temperatureUnit");
__decorateClass$4([
  n2({ type: Number })
], PresetDialog.prototype, "minDeadband");
__decorateClass$4([
  n2({ type: Number })
], PresetDialog.prototype, "minTemp");
__decorateClass$4([
  n2({ type: Number })
], PresetDialog.prototype, "maxTemp");
__decorateClass$4([
  r()
], PresetDialog.prototype, "currentMode");
__decorateClass$4([
  r()
], PresetDialog.prototype, "heatTo");
__decorateClass$4([
  r()
], PresetDialog.prototype, "coolTo");
__decorateClass$4([
  r()
], PresetDialog.prototype, "splitMinute");
if (!customElements.get("preset-dialog")) {
  customElements.define("preset-dialog", PresetDialog);
}
var __defProp$3 = Object.defineProperty;
var __decorateClass$3 = (decorators, target, key, kind) => {
  var result = void 0;
  for (var i2 = decorators.length - 1, decorator; i2 >= 0; i2--)
    if (decorator = decorators[i2])
      result = decorator(target, key, result) || result;
  if (result) __defProp$3(target, key, result);
  return result;
};
const _SchedulePresetCardEditor = class _SchedulePresetCardEditor extends i {
  setConfig(config) {
    this._config = {
      step_size: 15,
      temperature_unit: "°F",
      min_deadband: 2,
      ...config,
      type: "custom:schedule-preset-card"
    };
  }
  _valueChanged(key, value) {
    if (!this._config) return;
    this._config = {
      ...this._config,
      [key]: value
    };
    this.dispatchEvent(
      new CustomEvent("config-changed", {
        detail: { config: this._config },
        bubbles: true,
        composed: true
      })
    );
  }
  render() {
    var _a2;
    if (!this._config) return b``;
    const scheduleEntities = Object.keys(((_a2 = this.hass) == null ? void 0 : _a2.states) || {}).filter((entityId) => {
      var _a3, _b;
      if (!entityId.startsWith("schedule.")) return false;
      const stateObj = (_a3 = this.hass) == null ? void 0 : _a3.states[entityId];
      return ((_b = stateObj == null ? void 0 : stateObj.attributes) == null ? void 0 : _b.editable) !== false;
    }).sort();
    return b`
      <div class="editor-container">
        <!-- Target Schedule Entity -->
        <div class="form-row">
          <label class="form-label">Default Schedule Entity (optional)</label>
          <select
            class="form-select"
            .value=${this._config.entity || ""}
            @change=${(e2) => this._valueChanged("entity", e2.target.value)}
          >
            <option value="">(All schedules selectable in card)</option>
            ${scheduleEntities.map((id) => {
      var _a3, _b, _c;
      const friendlyName = ((_c = (_b = (_a3 = this.hass) == null ? void 0 : _a3.states[id]) == null ? void 0 : _b.attributes) == null ? void 0 : _c.friendly_name) || id;
      return b`
                <option value=${id} ?selected=${this._config.entity === id}>
                  ${friendlyName} (${id})
                </option>
              `;
    })}
          </select>
          <span style="font-size: 0.75rem; color: var(--secondary-text-color, #9ca3af);">
            Note: Only UI-created schedules are shown. YAML-defined schedules are static and not editable via GUI.
          </span>
        </div>

        <!-- Card Title -->
        <div class="form-row">
          <label class="form-label">Card Title (optional)</label>
          <input
            type="text"
            class="form-input"
            placeholder="e.g. First Floor Climate Schedule"
            .value=${this._config.title || ""}
            @input=${(e2) => this._valueChanged("title", e2.target.value)}
          />
        </div>

        <!-- Settings Grid -->
        <div class="form-grid">
          <!-- Temperature Unit -->
          <div class="form-row">
            <label class="form-label">Temperature Unit</label>
            <div class="unit-selector">
              <button
                type="button"
                class="unit-btn ${this._config.temperature_unit !== "°C" ? "active" : ""}"
                @click=${() => this._valueChanged("temperature_unit", "°F")}
              >°F</button>
              <button
                type="button"
                class="unit-btn ${this._config.temperature_unit === "°C" ? "active" : ""}"
                @click=${() => this._valueChanged("temperature_unit", "°C")}
              >°C</button>
            </div>
          </div>

          <!-- Time Step Size -->
          <div class="form-row">
            <label class="form-label">Snapping Interval</label>
            <select
              class="form-select"
              .value=${String(this._config.step_size || 15)}
              @change=${(e2) => this._valueChanged("step_size", parseInt(e2.target.value, 10))}
            >
              <option value="15" ?selected=${(this._config.step_size || 15) === 15}>15 Minutes</option>
              <option value="30" ?selected=${this._config.step_size === 30}>30 Minutes</option>
              <option value="60" ?selected=${this._config.step_size === 60}>60 Minutes</option>
            </select>
          </div>
        </div>

        <!-- Minimum Deadband -->
        <div class="form-row">
          <label class="form-label">Min Deadband Between Heat & Cool</label>
          <input
            type="number"
            class="form-input"
            min="0"
            max="15"
            step="1"
            .value=${String(this._config.min_deadband ?? 2)}
            @input=${(e2) => this._valueChanged("min_deadband", parseFloat(e2.target.value) || 0)}
          />
        </div>
      </div>
    `;
  }
};
_SchedulePresetCardEditor.styles = i$3`
    :host {
      display: block;
      font-family: var(--paper-font-body1_-_font-family, Roboto, sans-serif);
      color: var(--primary-text-color, #e1e7ec);
    }

    .editor-container {
      display: flex;
      flex-direction: column;
      gap: 16px;
      padding: 12px 4px;
    }

    .form-row {
      display: flex;
      flex-direction: column;
      gap: 6px;
    }

    .form-label {
      font-size: 0.88rem;
      font-weight: 500;
      color: var(--secondary-text-color, #9ca3af);
    }

    .form-input,
    .form-select {
      background: var(--input-idle-line-color, rgba(255, 255, 255, 0.08));
      color: var(--primary-text-color, #ffffff);
      border: 1px solid var(--divider-color, rgba(255, 255, 255, 0.15));
      border-radius: 8px;
      padding: 10px 12px;
      font-size: 0.92rem;
      box-sizing: border-box;
      width: 100%;
      outline: none;
      transition: border-color 0.15s;
    }

    .form-input:focus,
    .form-select:focus {
      border-color: var(--primary-color, #38bdf8);
    }

    .form-select {
      color-scheme: dark;
    }
    .form-select optgroup {
      background: var(--card-background-color, var(--ha-card-background, #1e293b));
      color: var(--secondary-text-color, #9ca3af);
    }
    .form-select option {
      background: var(--card-background-color, var(--ha-card-background, #1e293b));
      color: var(--primary-text-color, #ffffff);
    }

    .form-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 14px;
    }

    .unit-selector {
      display: flex;
      border-radius: 8px;
      overflow: hidden;
      border: 1px solid var(--divider-color, rgba(255, 255, 255, 0.15));
    }

    .unit-btn {
      flex: 1;
      padding: 8px 12px;
      background: rgba(255, 255, 255, 0.05);
      border: none;
      color: var(--secondary-text-color, #9ca3af);
      cursor: pointer;
      font-weight: 600;
      font-size: 0.9rem;
      transition: all 0.15s;
    }

    .unit-btn.active {
      background: var(--primary-color, #38bdf8);
      color: #0f172a;
    }
  `;
let SchedulePresetCardEditor = _SchedulePresetCardEditor;
__decorateClass$3([
  n2({ attribute: false })
], SchedulePresetCardEditor.prototype, "hass");
__decorateClass$3([
  r()
], SchedulePresetCardEditor.prototype, "_config");
if (!customElements.get("schedule-preset-card-editor")) {
  customElements.define("schedule-preset-card-editor", SchedulePresetCardEditor);
}
var __defProp$2 = Object.defineProperty;
var __decorateClass$2 = (decorators, target, key, kind) => {
  var result = void 0;
  for (var i2 = decorators.length - 1, decorator; i2 >= 0; i2--)
    if (decorator = decorators[i2])
      result = decorator(target, key, result) || result;
  if (result) __defProp$2(target, key, result);
  return result;
};
const _SchedulePresetCard = class _SchedulePresetCard extends i {
  constructor() {
    super(...arguments);
    this.schedules = [];
    this.selectedScheduleId = "";
    this.blocksByDay = {
      monday: [],
      tuesday: [],
      wednesday: [],
      thursday: [],
      friday: [],
      saturday: [],
      sunday: []
    };
    this.activeEditingBlock = null;
    this.isSaving = false;
    this.isYamlSchedule = false;
    this.isCompact = false;
    this.isEditMode = false;
    this.isForeign = false;
    this.dragAction = null;
    this.lastDragEndTime = 0;
    this._lastLoadedScheduleHash = "";
  }
  setConfig(config) {
    if (!config) {
      throw new Error("Invalid configuration");
    }
    this.config = {
      step_size: 15,
      temperature_unit: "°F",
      min_deadband: 2,
      min_temp: 45,
      max_temp: 85,
      ...config
    };
  }
  getCardSize() {
    return 10;
  }
  static async getConfigElement() {
    return document.createElement("schedule-preset-card-editor");
  }
  static getStubConfig() {
    return {
      type: "custom:schedule-preset-card",
      title: "Climate Schedule",
      temperature_unit: "°F",
      step_size: 15,
      min_deadband: 2
    };
  }
  connectedCallback() {
    super.connectedCallback();
    try {
      const savedCompact = localStorage.getItem("schedule-preset-card-compact");
      if (savedCompact !== null) {
        this.isCompact = savedCompact === "true";
      }
    } catch {
    }
    this._unsubscribeSync = subscribeScheduleUpdates((scheduleId) => {
      this.syncFromHass(true);
    });
  }
  disconnectedCallback() {
    super.disconnectedCallback();
    if (this._unsubscribeSync) {
      this._unsubscribeSync();
      this._unsubscribeSync = void 0;
    }
    if (this._heartbeatTimer) {
      clearInterval(this._heartbeatTimer);
      this._heartbeatTimer = void 0;
    }
    if (this.isEditMode) {
      this.sendLockSignal(false);
    }
  }
  sendLockSignal(acquire) {
    var _a2, _b;
    if (!this.hass || !this.selectedScheduleId) return;
    const action = acquire ? "acquire_schedule_lock" : "release_schedule_lock";
    if (!((_b = (_a2 = this.hass.services) == null ? void 0 : _a2.hvac_fusion) == null ? void 0 : _b[action])) return;
    this.hass.callService("hvac_fusion", action, {
      schedule_id: this.selectedScheduleId,
      ...acquire ? { duration: 300 } : {}
    });
  }
  toggleEditMode() {
    if (this.isYamlSchedule || this.isForeign) return;
    this.isEditMode = !this.isEditMode;
    if (this.isEditMode) {
      this.sendLockSignal(true);
      if (this._heartbeatTimer) clearInterval(this._heartbeatTimer);
      this._heartbeatTimer = setInterval(() => {
        if (this.isEditMode) this.sendLockSignal(true);
      }, 6e4);
    } else {
      if (this._heartbeatTimer) {
        clearInterval(this._heartbeatTimer);
        this._heartbeatTimer = void 0;
      }
      this.sendLockSignal(false);
    }
  }
  toggleCompact() {
    this.isCompact = !this.isCompact;
    try {
      localStorage.setItem("schedule-preset-card-compact", String(this.isCompact));
    } catch {
    }
  }
  willUpdate(changedProps) {
    if (changedProps.has("hass") && this.hass) {
      this.syncFromHass();
    }
  }
  async syncFromHass(forceReload = false) {
    if (!this.hass || this.isSaving || this.dragAction || this.activeEditingBlock) return;
    const list = await fetchScheduleList(this.hass);
    this.schedules = list;
    let targetId = null;
    try {
      targetId = localStorage.getItem("schedule-preset-card-selected");
    } catch {
    }
    if (!targetId || !list.some((s2) => s2.id === targetId)) {
      if (this.config.entity) {
        const found = findScheduleInList(list, this.config.entity, this.hass);
        if (found) {
          targetId = found.id;
        } else {
          targetId = this.config.entity.replace(/^schedule\./, "");
        }
      }
    }
    if ((!targetId || !list.some((s2) => s2.id === targetId)) && list.length > 0) {
      targetId = list[0].id;
    }
    if (targetId) {
      const item = list.find((s2) => s2.id === targetId);
      const itemHash = item ? JSON.stringify(item) : "";
      if (forceReload || targetId !== this.selectedScheduleId || itemHash && itemHash !== this._lastLoadedScheduleHash) {
        this.selectedScheduleId = targetId;
        this._lastLoadedScheduleHash = itemHash;
        this.loadScheduleBlocks(targetId);
      }
    }
  }
  loadScheduleBlocks(scheduleId) {
    const item = this.schedules.find((s2) => s2.id === scheduleId);
    if (item) {
      this._lastLoadedScheduleHash = JSON.stringify(item);
      this.blocksByDay = convertToInternalBlocks(item);
      this.isYamlSchedule = false;
      this.isForeign = isForeignSchedule(item);
      if (this.isForeign && this.isEditMode) {
        this.isEditMode = false;
        this.sendLockSignal(false);
      }
    } else {
      this.isYamlSchedule = true;
      this.isForeign = false;
    }
  }
  handleScheduleSelected(e2) {
    const select = e2.target;
    if (this.isEditMode) {
      this.sendLockSignal(false);
    }
    this.selectedScheduleId = select.value;
    try {
      localStorage.setItem("schedule-preset-card-selected", select.value);
    } catch {
    }
    if (this.isEditMode) {
      this.sendLockSignal(true);
    }
    this.loadScheduleBlocks(select.value);
  }
  // --- Interaction: Dragging, Resizing, and Creating Blocks ---
  handleTrackPointerDown(e2, day) {
    if (this.isYamlSchedule || !this.isEditMode) return;
    const track = e2.currentTarget;
    const rect = track.getBoundingClientRect();
    const clickY = e2.clientY - rect.top;
    const ratio = Math.max(0, Math.min(1, clickY / rect.height));
    const stepSize = this.config.step_size || 15;
    const clickedMinute = snapMinutes(ratio * 1440, stepSize);
    track.setPointerCapture(e2.pointerId);
    this.dragAction = {
      type: "create",
      day,
      initialY: e2.clientY,
      initialMinute: clickedMinute,
      currentMinute: clickedMinute,
      hasDragged: false
    };
  }
  handleBlockClick(e2, block) {
    var _a2;
    e2.stopPropagation();
    if (this.isYamlSchedule || !this.isEditMode) return;
    if (Date.now() - this.lastDragEndTime < 350 || ((_a2 = this.dragAction) == null ? void 0 : _a2.hasDragged)) return;
    this.activeEditingBlock = block;
  }
  handleResizePointerDown(e2, block, type) {
    if (this.isYamlSchedule || !this.isEditMode) return;
    e2.stopPropagation();
    e2.target.setPointerCapture(e2.pointerId);
    const blockList = this.blocksByDay[block.day];
    let abuttingBlockId;
    if (type === "resize-end") {
      const neighbor = blockList.find((b2) => b2.id !== block.id && b2.startMinutes === block.endMinutes);
      if (neighbor) abuttingBlockId = neighbor.id;
    } else if (type === "resize-start") {
      const neighbor = blockList.find((b2) => b2.id !== block.id && b2.endMinutes === block.startMinutes);
      if (neighbor) abuttingBlockId = neighbor.id;
    }
    this.dragAction = {
      type,
      blockId: block.id,
      abuttingBlockId,
      day: block.day,
      initialY: e2.clientY,
      initialMinute: type === "resize-start" ? block.startMinutes : block.endMinutes,
      currentMinute: type === "resize-start" ? block.startMinutes : block.endMinutes,
      initialStart: block.startMinutes,
      initialEnd: block.endMinutes,
      hasDragged: false
    };
  }
  handleTrackPointerMove(e2, day) {
    if (!this.dragAction || this.dragAction.day !== day) return;
    if (Math.abs(e2.clientY - this.dragAction.initialY) > 5) {
      this.dragAction.hasDragged = true;
    }
    const track = e2.currentTarget;
    const rect = track.getBoundingClientRect();
    const currentY = e2.clientY - rect.top;
    const ratio = Math.max(0, Math.min(1, currentY / rect.height));
    const stepSize = this.config.step_size || 15;
    const currentMinute = snapMinutes(ratio * 1440, stepSize);
    const { type, blockId, abuttingBlockId, initialMinute } = this.dragAction;
    const blockList = this.blocksByDay[day];
    if (type === "create") {
      if (!this.dragAction.hasDragged) return;
      this.dragAction.currentMinute = currentMinute;
      this.requestUpdate();
      return;
    }
    const currentBlock = blockList.find((b2) => b2.id === blockId);
    if (!currentBlock) return;
    if (type === "resize-start") {
      const nextStart = Math.min(currentBlock.endMinutes - stepSize, Math.max(0, currentMinute));
      this.dragAction.currentMinute = nextStart;
      if (nextStart !== currentBlock.startMinutes) {
        currentBlock.startMinutes = nextStart;
        if (abuttingBlockId) {
          const neighbor = blockList.find((b2) => b2.id === abuttingBlockId);
          if (neighbor) {
            neighbor.endMinutes = nextStart;
          }
        }
      }
      this.requestUpdate();
    } else if (type === "resize-end") {
      const nextEnd = Math.max(currentBlock.startMinutes + stepSize, Math.min(1440, currentMinute));
      this.dragAction.currentMinute = nextEnd;
      if (nextEnd !== currentBlock.endMinutes) {
        currentBlock.endMinutes = nextEnd;
        if (abuttingBlockId) {
          const neighbor = blockList.find((b2) => b2.id === abuttingBlockId);
          if (neighbor) {
            neighbor.startMinutes = nextEnd;
          }
        }
      }
      this.requestUpdate();
    }
  }
  handleTrackPointerUp() {
    if (!this.dragAction) return;
    const { type, day, initialMinute, hasDragged } = this.dragAction;
    if (type === "create") {
      if (!hasDragged) {
        const existing = this.blocksByDay[day].find(
          (b2) => initialMinute >= b2.startMinutes && initialMinute < b2.endMinutes
        );
        if (existing) {
          this.activeEditingBlock = existing;
        } else {
          this.config.step_size || 15;
          const newStart = initialMinute;
          const newEnd = Math.min(1440, newStart + 60);
          const newBlock = {
            id: `${day}_block_${Date.now()}`,
            day,
            startMinutes: newStart,
            endMinutes: newEnd,
            hvac_mode: "heat_cool",
            heat_to: 68,
            cool_to: 74
          };
          this.blocksByDay = {
            ...this.blocksByDay,
            [day]: [...this.blocksByDay[day], newBlock].sort((a2, b2) => a2.startMinutes - b2.startMinutes)
          };
          this.activeEditingBlock = newBlock;
        }
      } else {
        const stepSize = this.config.step_size || 15;
        const curMin = this.dragAction.currentMinute ?? initialMinute;
        const start = Math.min(initialMinute, curMin);
        const end = Math.max(start + stepSize, Math.max(initialMinute, curMin));
        this.carveAndInsertBlock(day, start, Math.min(1440, end));
      }
    }
    if (hasDragged) {
      this.lastDragEndTime = Date.now();
    }
    this.dragAction = null;
    this.saveCurrentSchedule();
  }
  carveAndInsertBlock(day, carveStart, carveEnd) {
    const blockList = this.blocksByDay[day];
    const nextBlocks = [];
    const intersected = blockList.find(
      (b2) => b2.startMinutes < carveEnd && b2.endMinutes > carveStart
    );
    for (const b2 of blockList) {
      if (b2.endMinutes <= carveStart || b2.startMinutes >= carveEnd) {
        nextBlocks.push(b2);
      } else if (b2.startMinutes < carveStart && b2.endMinutes > carveEnd) {
        nextBlocks.push({
          ...b2,
          id: `${b2.day}_block_${Date.now()}_left`,
          endMinutes: carveStart
        });
        nextBlocks.push({
          ...b2,
          id: `${b2.day}_block_${Date.now()}_right`,
          startMinutes: carveEnd
        });
      } else if (b2.startMinutes < carveStart && b2.endMinutes > carveStart && b2.endMinutes <= carveEnd) {
        nextBlocks.push({
          ...b2,
          endMinutes: carveStart
        });
      } else if (b2.startMinutes >= carveStart && b2.startMinutes < carveEnd && b2.endMinutes > carveEnd) {
        nextBlocks.push({
          ...b2,
          startMinutes: carveEnd
        });
      }
    }
    const newBlock = {
      id: `${day}_block_${Date.now()}`,
      day,
      startMinutes: carveStart,
      endMinutes: carveEnd,
      hvac_mode: (intersected == null ? void 0 : intersected.hvac_mode) || "heat_cool",
      heat_to: (intersected == null ? void 0 : intersected.heat_to) ?? 68,
      cool_to: (intersected == null ? void 0 : intersected.cool_to) ?? 74
    };
    nextBlocks.push(newBlock);
    nextBlocks.sort((a2, b2) => a2.startMinutes - b2.startMinutes);
    this.blocksByDay = {
      ...this.blocksByDay,
      [day]: nextBlocks
    };
  }
  handleSplitBlock(e2) {
    const { blockId, day, splitMinute } = e2.detail;
    const blockList = this.blocksByDay[day];
    const index = blockList.findIndex((b2) => b2.id === blockId);
    if (index === -1) return;
    const original = blockList[index];
    const originalEnd = original.endMinutes;
    original.endMinutes = splitMinute;
    const secondPiece = {
      ...original,
      id: `${day}_block_${Date.now()}`,
      startMinutes: splitMinute,
      endMinutes: originalEnd
    };
    const nextList = [...blockList, secondPiece].sort((a2, b2) => a2.startMinutes - b2.startMinutes);
    this.blocksByDay = {
      ...this.blocksByDay,
      [day]: nextList
    };
    this.activeEditingBlock = null;
    this.saveCurrentSchedule();
  }
  // --- Block Dialog Event Handlers ---
  handleSaveBlock(e2) {
    const updated = e2.detail.block;
    const day = updated.day;
    const list = this.blocksByDay[day].map((b2) => b2.id === updated.id ? updated : b2);
    this.blocksByDay = {
      ...this.blocksByDay,
      [day]: list
    };
    this.activeEditingBlock = null;
    this.saveCurrentSchedule();
  }
  handleDeleteBlock(e2) {
    const { blockId, day } = e2.detail;
    this.blocksByDay = {
      ...this.blocksByDay,
      [day]: this.blocksByDay[day].filter((b2) => b2.id !== blockId)
    };
    this.activeEditingBlock = null;
    this.saveCurrentSchedule();
  }
  handleCopyBlockTo(e2) {
    const { block, target } = e2.detail;
    const targetDays = target === "weekdays" ? ["monday", "tuesday", "wednesday", "thursday", "friday"] : target === "weekend" ? ["saturday", "sunday"] : DAYS_OF_WEEK;
    const nextBlocks = { ...this.blocksByDay };
    for (const day of targetDays) {
      const copy = {
        ...block,
        id: `${day}_block_${Date.now()}_${Math.random()}`,
        day
      };
      nextBlocks[day] = [
        ...nextBlocks[day].filter(
          (b2) => !(b2.startMinutes < copy.endMinutes && b2.endMinutes > copy.startMinutes)
        ),
        copy
      ].sort((a2, b2) => a2.startMinutes - b2.startMinutes);
    }
    this.blocksByDay = nextBlocks;
    this.activeEditingBlock = null;
    this.saveCurrentSchedule();
  }
  async saveCurrentSchedule() {
    if (this.isYamlSchedule || !this.hass || !this.selectedScheduleId) return;
    this.isSaving = true;
    try {
      const schedule = this.schedules.find((s2) => s2.id === this.selectedScheduleId);
      const name = (schedule == null ? void 0 : schedule.name) || this.selectedScheduleId;
      const icon = schedule == null ? void 0 : schedule.icon;
      const haDays = convertToHABlocks(this.blocksByDay);
      await updateHASchedule(this.hass, this.selectedScheduleId, name, haDays, icon);
      this._lastLoadedScheduleHash = JSON.stringify({ ...schedule, ...haDays, name, icon });
    } catch (err) {
      console.error("[schedule-preset-card] Failed to save schedule update:", err);
    } finally {
      this.isSaving = false;
    }
  }
  // --- Rendering ---
  renderGridLines() {
    const step = this.isCompact ? 4 : 2;
    const lines = [];
    for (let hour = step; hour < 24; hour += step) {
      const topPct = hour / 24 * 100;
      lines.push(
        b`<div class="grid-line" style="top: ${topPct}%;"></div>`
      );
    }
    return lines;
  }
  renderBlockCell(block) {
    const trackHeightPx = this.isCompact ? 348 : 548;
    const startPct = block.startMinutes / 1440 * 100;
    const duration = block.endMinutes - block.startMinutes;
    const heightPct = duration / 1440 * 100;
    const heightPx = duration / 1440 * trackHeightPx;
    const unit = this.config.temperature_unit || "°F";
    const heatColor = getHeatColor(block.heat_to, unit);
    const coolColor = getCoolColor(block.cool_to, unit);
    const heatText = getHeatTextColor(block.heat_to, unit);
    const coolText = getCoolTextColor(block.cool_to, unit);
    const tooltip = block.hvac_mode === "heat_cool" ? `Dual: Heat ${block.heat_to}°, Cool ${block.cool_to}° (${formatTimeDisplay(block.startMinutes)} – ${formatTimeDisplay(block.endMinutes)})` : block.hvac_mode === "heat" ? `Heat: ${block.heat_to}° (${formatTimeDisplay(block.startMinutes)} – ${formatTimeDisplay(block.endMinutes)})` : block.hvac_mode === "cool" ? `Cool: ${block.cool_to}° (${formatTimeDisplay(block.startMinutes)} – ${formatTimeDisplay(block.endMinutes)})` : `Off (${formatTimeDisplay(block.startMinutes)} – ${formatTimeDisplay(block.endMinutes)})`;
    const estimatedWidthPx = 60;
    const orientation = getSplitOrientation(estimatedWidthPx, heightPx);
    if (block.isGeneric) {
      const genericTooltip = `Non-Climate Block: No HVAC targets (${formatTimeDisplay(block.startMinutes)} – ${formatTimeDisplay(block.endMinutes)})`;
      return b`
        <div
          class="schedule-cell cell-generic"
          style="top: ${startPct}%; height: ${heightPct}%;"
          title=${genericTooltip}
          @click=${(e2) => this.handleBlockClick(e2, block)}
        >
          <div class="generic-cell-content">
            ${heightPx >= 28 ? "No HVAC" : ""}
          </div>
          <div
            class="resize-handle top"
            @click=${(e2) => e2.stopPropagation()}
            @pointerdown=${(e2) => this.handleResizePointerDown(e2, block, "resize-start")}
          ></div>
          <div
            class="resize-handle bottom"
            @click=${(e2) => e2.stopPropagation()}
            @pointerdown=${(e2) => this.handleResizePointerDown(e2, block, "resize-end")}
          ></div>
        </div>
      `;
    }
    if (block.hvac_mode === "off") {
      return b`
        <div
          class="schedule-cell cell-off"
          style="top: ${startPct}%; height: ${heightPct}%;"
          title=${tooltip}
          @click=${(e2) => this.handleBlockClick(e2, block)}
        >
          ${heightPx >= 28 ? "Off" : ""}
          <div
            class="resize-handle top"
            @click=${(e2) => e2.stopPropagation()}
            @pointerdown=${(e2) => this.handleResizePointerDown(e2, block, "resize-start")}
          ></div>
          <div
            class="resize-handle bottom"
            @click=${(e2) => e2.stopPropagation()}
            @pointerdown=${(e2) => this.handleResizePointerDown(e2, block, "resize-end")}
          ></div>
        </div>
      `;
    }
    if (block.hvac_mode === "heat") {
      return b`
        <div
          class="schedule-cell"
          style="top: ${startPct}%; height: ${heightPct}%; background-color: ${heatColor}; color: ${heatText};"
          title=${tooltip}
          @click=${(e2) => this.handleBlockClick(e2, block)}
        >
          <div style="flex: 1; display: flex; align-items: center; justify-content: center; font-weight: 700; font-size: 0.78rem;">
            ${heightPx >= 20 ? `${block.heat_to}°` : ""}
          </div>
          <div
            class="resize-handle top"
            @click=${(e2) => e2.stopPropagation()}
            @pointerdown=${(e2) => this.handleResizePointerDown(e2, block, "resize-start")}
          ></div>
          <div
            class="resize-handle bottom"
            @click=${(e2) => e2.stopPropagation()}
            @pointerdown=${(e2) => this.handleResizePointerDown(e2, block, "resize-end")}
          ></div>
        </div>
      `;
    }
    if (block.hvac_mode === "cool") {
      return b`
        <div
          class="schedule-cell"
          style="top: ${startPct}%; height: ${heightPct}%; background-color: ${coolColor}; color: ${coolText};"
          title=${tooltip}
          @click=${(e2) => this.handleBlockClick(e2, block)}
        >
          <div style="flex: 1; display: flex; align-items: center; justify-content: center; font-weight: 700; font-size: 0.78rem;">
            ${heightPx >= 20 ? `${block.cool_to}°` : ""}
          </div>
          <div
            class="resize-handle top"
            @click=${(e2) => e2.stopPropagation()}
            @pointerdown=${(e2) => this.handleResizePointerDown(e2, block, "resize-start")}
          ></div>
          <div
            class="resize-handle bottom"
            @click=${(e2) => e2.stopPropagation()}
            @pointerdown=${(e2) => this.handleResizePointerDown(e2, block, "resize-end")}
          ></div>
        </div>
      `;
    }
    const isStacked = orientation === "stacked";
    return b`
      <div
        class="schedule-cell ${isStacked ? "stacked" : "side-by-side"}"
        style="top: ${startPct}%; height: ${heightPct}%;"
        title=${tooltip}
        @click=${(e2) => this.handleBlockClick(e2, block)}
      >
        ${isStacked ? b`
              <!-- Top band: Cooling -->
              <div class="cool-band" style="background-color: ${coolColor}; color: ${coolText};">
                ${heightPx >= 48 ? `${block.cool_to}°` : ""}
              </div>
              <!-- Bottom band: Heating -->
              <div class="heat-band" style="background-color: ${heatColor}; color: ${heatText};">
                ${heightPx >= 48 ? `${block.heat_to}°` : ""}
              </div>
            ` : b`
              <!-- Rotated Side-by-side for short duration blocks -->
              <!-- Left band: Heating -->
              <div class="heat-band" style="background-color: ${heatColor}; color: ${heatText};">
                ${heightPx >= 16 ? `${block.heat_to}°` : ""}
              </div>
              <!-- Right band: Cooling -->
              <div class="cool-band" style="background-color: ${coolColor}; color: ${coolText};">
                ${heightPx >= 16 ? `${block.cool_to}°` : ""}
              </div>
            `}

        <div
          class="resize-handle top"
          @pointerdown=${(e2) => this.handleResizePointerDown(e2, block, "resize-start")}
        ></div>
        <div
          class="resize-handle bottom"
          @pointerdown=${(e2) => this.handleResizePointerDown(e2, block, "resize-end")}
        ></div>
      </div>
    `;
  }
  render() {
    var _a2, _b;
    const title = ((_a2 = this.config) == null ? void 0 : _a2.title) || "Climate Schedule";
    const currentScheduleName = ((_b = this.schedules.find((s2) => s2.id === this.selectedScheduleId)) == null ? void 0 : _b.name) || this.selectedScheduleId || "Schedule";
    const todayIndex = ((/* @__PURE__ */ new Date()).getDay() + 6) % 7;
    const todayKey = DAYS_OF_WEEK[todayIndex];
    return b`
      <ha-card>
        <!-- Header -->
        <div class="card-header-row">
          <div class="title-row">
            <h2 class="card-title" title="${title}">${title}</h2>
            ${this.isYamlSchedule ? b`<span class="yaml-badge" title="Defined in YAML: edits must be made in configuration.yaml">YAML (Read Only)</span>` : this.isForeign ? b`<span class="yaml-badge" title="Non-HVAC schedule data payloads cannot be edited in this card">Non-HVAC (Read Only)</span>` : ""}
          </div>

          <div class="header-actions">
            ${this.schedules.length > 0 ? b`
                  <select class="schedule-select" @change=${this.handleScheduleSelected}>
                    ${(() => {
      const climateSchedules = this.schedules.filter((s2) => !isForeignSchedule(s2));
      const foreignSchedules = this.schedules.filter((s2) => isForeignSchedule(s2));
      if (foreignSchedules.length > 0 && climateSchedules.length > 0) {
        return b`
                          <optgroup label="Climate Schedules">
                            ${climateSchedules.map(
          (s2) => b`
                                <option value=${s2.id} ?selected=${s2.id === this.selectedScheduleId}>
                                  ${s2.name || s2.id}
                                </option>
                              `
        )}
                          </optgroup>
                          <optgroup label="Other Schedules">
                            ${foreignSchedules.map(
          (s2) => b`
                                <option value=${s2.id} ?selected=${s2.id === this.selectedScheduleId}>
                                  ${s2.name || s2.id} (non-HVAC)
                                </option>
                              `
        )}
                          </optgroup>
                        `;
      }
      return this.schedules.map(
        (s2) => b`
                          <option value=${s2.id} ?selected=${s2.id === this.selectedScheduleId}>
                            ${s2.name || s2.id}${isForeignSchedule(s2) ? " (non-HVAC)" : ""}
                          </option>
                        `
      );
    })()}
                  </select>
                ` : b`<span style="font-size: 0.85rem; color: var(--secondary-text-color, #a1a1aa);">${currentScheduleName}</span>`}

            <!-- Edit mode toggle -->
            <button
              class="edit-toggle-btn ${this.isEditMode ? "active" : ""}"
              @click=${this.toggleEditMode}
              ?disabled=${this.isYamlSchedule || this.isForeign}
              title=${this.isYamlSchedule ? "YAML schedules are read-only" : this.isForeign ? "Non-HVAC schedules are read-only" : this.isEditMode ? "Finish editing" : "Enable editing"}
            >
              ${this.isEditMode ? "✓ Done" : "✎ Edit"}
            </button>
          </div>
        </div>

        <!-- 7-Day Timeline Grid -->
        <div class="timeline-container ${this.isCompact ? "compact" : ""} ${this.isEditMode ? "editing" : ""}">
          <!-- Time Axis -->
          <div class="time-axis">
            ${(this.isCompact ? [0, 4, 8, 12, 16, 20, 24] : [0, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22, 24]).map((hour) => {
      return b`
                <div class="time-tick" style="top: calc(32px + (100% - 32px) * ${hour / 24});">
                  ${String(hour).padStart(2, "0")}:00
                </div>
              `;
    })}
          </div>

          <!-- Day Columns -->
          <div class="days-container">
            ${DAYS_OF_WEEK.map((day) => {
      const blocks = this.blocksByDay[day] || [];
      const isToday = day === todayKey;
      return b`
                <div class="day-column">
                  <div class="day-header ${isToday ? "today" : ""}">
                    ${DAY_LABELS[day].short}
                  </div>

                  <div
                    class="day-track"
                    @pointerdown=${(e2) => this.handleTrackPointerDown(e2, day)}
                    @pointermove=${(e2) => this.handleTrackPointerMove(e2, day)}
                    @pointerup=${this.handleTrackPointerUp}
                  >
                    ${this.renderGridLines()}
                    ${blocks.map((block) => this.renderBlockCell(block))}
                    ${this.dragAction && this.dragAction.day === day && this.dragAction.type === "create" && this.dragAction.hasDragged ? (() => {
        const step = this.config.step_size || 15;
        const cur = this.dragAction.currentMinute ?? this.dragAction.initialMinute;
        const start = Math.min(this.dragAction.initialMinute, cur);
        const end = Math.min(1440, Math.max(start + step, Math.max(this.dragAction.initialMinute, cur)));
        const topPct = start / 1440 * 100;
        const heightPct = (end - start) / 1440 * 100;
        return b`
                            <div class="carve-preview" style="top: ${topPct}%; height: ${heightPct}%;">
                              <span class="carve-preview-label">${formatTimeDisplay(start)} – ${formatTimeDisplay(end)}</span>
                            </div>
                          `;
      })() : ""}
                    ${this.dragAction && this.dragAction.day === day && (this.dragAction.type === "resize-start" || this.dragAction.type === "resize-end") && this.dragAction.currentMinute !== void 0 ? (() => {
        const topPct = this.dragAction.currentMinute / 1440 * 100;
        return b`
                            <div class="drag-time-indicator" style="top: ${topPct}%;">
                              <div class="drag-time-line"></div>
                              <div class="drag-time-pill ${this.dragAction.currentMinute < 75 ? "flip-down" : ""}">${formatTimeDisplay(this.dragAction.currentMinute)}</div>
                            </div>
                          `;
      })() : ""}
                  </div>
                </div>
              `;
    })}
          </div>
        </div>

        <!-- Footer / Legend -->
        <div class="card-footer">
          <div class="legend">
            <div class="legend-item">
              <div class="legend-swatch" style="background: ${getHeatColor(70, this.config.temperature_unit)};"></div>
              <span>Heat</span>
            </div>
            <div class="legend-item">
              <div class="legend-swatch" style="background: ${getCoolColor(72, this.config.temperature_unit)};"></div>
              <span>Cool</span>
            </div>
            <div class="legend-item">
              <div class="legend-swatch" style="background: #27272a; border: 1px solid #52525b;"></div>
              <span>Off (Gap)</span>
            </div>
          </div>

          <div style="display: flex; align-items: center; gap: 12px;">
            <button class="view-toggle-btn" @click=${this.toggleCompact} title="Toggle card height">
              <span>↕</span> ${this.isCompact ? "Full View" : "Compact View"}
            </button>
            <span>${this.isSaving ? "Saving..." : this.isEditMode ? "Editing • Drag to carve / click block to edit" : "Locked • Click ✎ Edit to make changes"}</span>
          </div>
        </div>

        <!-- Active Preset Edit Dialog Modal -->
        ${this.activeEditingBlock ? b`
              <preset-dialog
                .block=${this.activeEditingBlock}
                .temperatureUnit=${this.config.temperature_unit || "°F"}
                .minDeadband=${this.config.min_deadband || 2}
                .minTemp=${this.config.min_temp || 45}
                .maxTemp=${this.config.max_temp || 85}
                @save-block=${this.handleSaveBlock}
                @delete-block=${this.handleDeleteBlock}
                @split-block=${this.handleSplitBlock}
                @copy-block-to=${this.handleCopyBlockTo}
                @close-dialog=${() => this.activeEditingBlock = null}
              ></preset-dialog>
            ` : ""}
      </ha-card>
    `;
  }
};
_SchedulePresetCard.styles = i$3`
    :host {
      display: block;
      font-family: var(--paper-font-body1_-_font-family, Roboto, sans-serif);
      color: var(--primary-text-color, #e1e7ec);
      user-select: none;
      -webkit-user-select: none;
    }

    ha-card {
      background: var(--ha-card-background, var(--card-background-color, #181c24));
      border-radius: var(--ha-card-border-radius, 16px);
      border: 1px solid var(--divider-color, rgba(255, 255, 255, 0.08));
      padding: 14px 16px;
      overflow: hidden;
      display: flex;
      flex-direction: column;
      gap: 10px;
    }

    /* Card Header */
    .card-header-row {
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: nowrap;
      gap: 10px;
      margin: 0;
      padding: 0;
      min-width: 0;
    }

    .title-row {
      display: flex;
      align-items: center;
      gap: 10px;
      min-width: 0;
      flex: 1 1 auto;
      overflow: hidden;
    }

    .card-title {
      font-size: 1.25rem;
      font-weight: 600;
      color: var(--primary-text-color, #ffffff);
      margin: 0;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
      min-width: 0;
      flex-shrink: 1;
    }

    .yaml-badge {
      font-size: 0.72rem;
      padding: 3px 8px;
      border-radius: 6px;
      background: rgba(234, 179, 8, 0.15);
      color: #eab308;
      border: 1px solid rgba(234, 179, 8, 0.3);
      white-space: nowrap;
      flex-shrink: 0;
    }

    .header-actions {
      display: flex;
      align-items: center;
      gap: 8px;
      flex-shrink: 0;
    }

    .schedule-select {
      color-scheme: dark;
      background: rgba(255, 255, 255, 0.08);
      color: var(--primary-text-color, #ffffff);
      border: 1px solid rgba(255, 255, 255, 0.15);
      border-radius: 8px;
      padding: 6px 10px;
      font-size: 0.85rem;
      cursor: pointer;
      max-width: 200px;
    }
    .schedule-select:focus {
      outline: none;
      border-color: var(--primary-color, #3b82f6);
    }
    .schedule-select optgroup {
      background: var(--card-background-color, var(--ha-card-background, #1e293b));
      color: var(--secondary-text-color, #9ca3af);
      font-weight: 600;
    }
    .schedule-select option {
      background: var(--card-background-color, var(--ha-card-background, #1e293b));
      color: var(--primary-text-color, #ffffff);
      font-weight: normal;
    }

    .non-climate-notice {
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 0.78rem;
      color: #cbd5e1;
      background: rgba(100, 116, 139, 0.2);
      border: 1px solid rgba(148, 163, 184, 0.3);
      border-radius: 6px;
      padding: 6px 10px;
      margin-top: 10px;
    }

    .edit-toggle-btn {
      background: rgba(255, 255, 255, 0.06);
      border: 1px solid rgba(255, 255, 255, 0.12);
      color: var(--secondary-text-color, #9ca3af);
      font-size: 0.78rem;
      font-weight: 600;
      padding: 4px 10px;
      border-radius: 6px;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 5px;
      transition: all 0.15s ease-in-out;
    }
    .edit-toggle-btn:hover:not(:disabled) {
      background: rgba(255, 255, 255, 0.12);
      color: #fff;
    }
    .edit-toggle-btn.active {
      background: rgba(56, 189, 248, 0.18);
      border-color: #38bdf8;
      color: #38bdf8;
    }
    .edit-toggle-btn:disabled {
      opacity: 0.4;
      cursor: not-allowed;
    }

    /* Weekly Grid Layout */
    .timeline-container {
      display: flex;
      width: 100%;
      height: 580px;
      position: relative;
      background: rgba(0, 0, 0, 0.22);
      border-radius: 12px;
      border: 1px solid rgba(255, 255, 255, 0.06);
      overflow: hidden;
      transition: height 0.22s ease-in-out;
    }

    .timeline-container.editing {
      border-color: rgba(56, 189, 248, 0.45);
    }
    .timeline-container.editing .timeline-block {
      cursor: pointer;
    }
    .timeline-container:not(.editing) .timeline-block {
      cursor: default;
    }
    .timeline-container:not(.editing) .resize-handle {
      display: none;
    }

    .timeline-container.compact {
      height: 280px;
    }

    /* Y-Axis Time Labels */
    .time-axis {
      width: 50px;
      flex-shrink: 0;
      position: relative;
      height: 100%;
      border-right: 1px solid rgba(255, 255, 255, 0.08);
      padding-top: 32px; /* space for day header */
      box-sizing: border-box;
    }

    .time-tick {
      position: absolute;
      left: 6px;
      font-size: 0.72rem;
      color: var(--secondary-text-color, #8b949e);
      transform: translateY(-50%);
      pointer-events: none;
    }

    /* Day Columns Container */
    .days-container {
      flex: 1;
      display: grid;
      grid-template-columns: repeat(7, 1fr);
      height: 100%;
      position: relative;
    }

    .day-column {
      display: flex;
      flex-direction: column;
      height: 100%;
      border-right: 1px solid rgba(255, 255, 255, 0.05);
      position: relative;
    }
    .day-column:last-child {
      border-right: none;
    }

    .day-header {
      height: 32px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 0.82rem;
      font-weight: 600;
      color: var(--secondary-text-color, #a1a1aa);
      border-bottom: 1px solid rgba(255, 255, 255, 0.08);
      background: rgba(255, 255, 255, 0.02);
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }
    .day-header.today {
      color: var(--primary-color, #38bdf8);
      font-weight: 700;
    }

    /* Day Track (00:00 to 24:00) */
    .day-track {
      flex: 1;
      position: relative;
      cursor: crosshair;
      touch-action: none;
    }

    /* Background 2-hour grid lines */
    .grid-line {
      position: absolute;
      left: 0;
      right: 0;
      height: 1px;
      background: rgba(255, 255, 255, 0.04);
      pointer-events: none;
    }

    /* Individual Block Cell */
    .schedule-cell {
      position: absolute;
      left: 3px;
      right: 3px;
      border-radius: 6px;
      overflow: hidden;
      cursor: pointer;
      box-shadow: 0 2px 4px rgba(0, 0, 0, 0.35);
      transition: box-shadow 0.15s, border-color 0.15s;
      border: 1px solid rgba(255, 255, 255, 0.15);
      box-sizing: border-box;
      display: flex;
    }

    .schedule-cell:hover {
      box-shadow: 0 4px 8px rgba(0, 0, 0, 0.5);
      border-color: rgba(255, 255, 255, 0.4);
      z-index: 10;
    }

    /* Stacked (Normal / Tall duration) */
    .schedule-cell.stacked {
      flex-direction: column;
    }

    .schedule-cell.stacked .cool-band,
    .schedule-cell.stacked .heat-band {
      flex: 1;
      width: 100%;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 0.76rem;
      font-weight: 700;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    /* Side-by-side (Rotated for short / horizontal duration) */
    .schedule-cell.side-by-side {
      flex-direction: row;
    }

    .schedule-cell.side-by-side .heat-band,
    .schedule-cell.side-by-side .cool-band {
      flex: 1;
      height: 100%;
      min-height: 0;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 0.65rem;
      font-weight: 700;
      line-height: 1;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    /* Resize Handles */
    .resize-handle {
      position: absolute;
      left: 0;
      right: 0;
      height: 8px;
      z-index: 20;
      cursor: ns-resize;
    }
    .resize-handle.top {
      top: 0;
    }
    .resize-handle.bottom {
      bottom: 0;
    }
    .resize-handle:hover {
      background: rgba(255, 255, 255, 0.25);
    }

    /* Off / Neutral block */
    .cell-off {
      background: #27272a !important;
      color: #71717a !important;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 0.75rem;
      font-weight: 600;
    }

    /* Generic non-climate block */
    .cell-generic {
      background: rgba(100, 116, 139, 0.35) !important;
      border: 1px dashed rgba(148, 163, 184, 0.7) !important;
      color: var(--secondary-text-color, #94a3b8) !important;
      display: flex;
    }
    .cell-generic:hover {
      background: rgba(100, 116, 139, 0.5) !important;
      border-color: #cbd5e1 !important;
    }
    .generic-cell-content {
      flex: 1;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 0.68rem;
      font-weight: 600;
      color: #cbd5e1;
      text-transform: uppercase;
      letter-spacing: 0.04em;
    }

    /* Carve preview overlay */
    .carve-preview {
      position: absolute;
      left: 3px;
      right: 3px;
      border: 2px dashed var(--primary-color, #38bdf8);
      background: rgba(56, 189, 248, 0.28);
      border-radius: 6px;
      pointer-events: none;
      z-index: 25;
      box-sizing: border-box;
      display: flex;
      align-items: center;
      justify-content: center;
    }

    .carve-preview-label {
      font-size: 0.72rem;
      font-weight: 700;
      color: #fff;
      background: rgba(0, 0, 0, 0.75);
      padding: 2px 6px;
      border-radius: 4px;
      white-space: nowrap;
    }

    /* Floating time indicator while dragging edges */
    .drag-time-indicator {
      position: absolute;
      left: -8px;
      right: -8px;
      height: 0;
      pointer-events: none;
      z-index: 50;
      display: flex;
      align-items: center;
      justify-content: center;
      transform: translateY(-50%);
    }

    .drag-time-line {
      position: absolute;
      left: 0;
      right: 0;
      height: 2px;
      background: var(--primary-color, #38bdf8);
      box-shadow: 0 0 8px rgba(56, 189, 248, 0.9);
    }

    .drag-time-pill {
      position: relative;
      background: #090d16;
      color: #38bdf8;
      border: 1.5px solid #38bdf8;
      padding: 3px 8px;
      border-radius: 8px;
      font-size: 0.76rem;
      font-weight: 700;
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.85);
      white-space: nowrap;
      letter-spacing: 0.5px;
      transform: translateY(-20px); /* Floats above the cursor and guideline */
      transition: transform 0.1s ease;
    }

    .drag-time-pill::after {
      content: '';
      position: absolute;
      bottom: -5px;
      left: 50%;
      transform: translateX(-50%);
      width: 0;
      height: 0;
      border-left: 5px solid transparent;
      border-right: 5px solid transparent;
      border-top: 5px solid #38bdf8;
    }

    /* Flip downward when dragging near the top of the day */
    .drag-time-pill.flip-down {
      transform: translateY(20px);
    }

    .drag-time-pill.flip-down::after {
      bottom: auto;
      top: -5px;
      border-top: none;
      border-bottom: 5px solid #38bdf8;
    }

    /* Footer hints */
    .card-footer {
      display: flex;
      justify-content: space-between;
      align-items: center;
      font-size: 0.78rem;
      color: var(--secondary-text-color, #71717a);
      padding: 0 4px;
    }

    .legend {
      display: flex;
      align-items: center;
      gap: 12px;
    }

    .legend-item {
      display: flex;
      align-items: center;
      gap: 5px;
    }

    .legend-swatch {
      width: 12px;
      height: 12px;
      border-radius: 3px;
    }

    .view-toggle-btn {
      display: inline-flex;
      align-items: center;
      gap: 5px;
      padding: 4px 10px;
      border-radius: 6px;
      background: rgba(255, 255, 255, 0.06);
      border: 1px solid rgba(255, 255, 255, 0.12);
      color: var(--secondary-text-color, #9ca3af);
      font-size: 0.75rem;
      font-weight: 500;
      cursor: pointer;
      transition: all 0.15s;
    }
    .view-toggle-btn:hover {
      background: rgba(255, 255, 255, 0.15);
      color: #fff;
    }
  `;
let SchedulePresetCard = _SchedulePresetCard;
__decorateClass$2([
  n2({ attribute: false })
], SchedulePresetCard.prototype, "hass");
__decorateClass$2([
  r()
], SchedulePresetCard.prototype, "config");
__decorateClass$2([
  r()
], SchedulePresetCard.prototype, "schedules");
__decorateClass$2([
  r()
], SchedulePresetCard.prototype, "selectedScheduleId");
__decorateClass$2([
  r()
], SchedulePresetCard.prototype, "blocksByDay");
__decorateClass$2([
  r()
], SchedulePresetCard.prototype, "activeEditingBlock");
__decorateClass$2([
  r()
], SchedulePresetCard.prototype, "isSaving");
__decorateClass$2([
  r()
], SchedulePresetCard.prototype, "isYamlSchedule");
__decorateClass$2([
  r()
], SchedulePresetCard.prototype, "isCompact");
__decorateClass$2([
  r()
], SchedulePresetCard.prototype, "isEditMode");
__decorateClass$2([
  r()
], SchedulePresetCard.prototype, "isForeign");
if (!customElements.get("schedule-preset-card")) {
  customElements.define("schedule-preset-card", SchedulePresetCard);
}
window.customCards = window.customCards || [];
window.customCards.push({
  type: "schedule-preset-card",
  name: "Climate Preset Schedule Card",
  description: "Visual 7-day schedule editor for climate dual-setpoints and native HA schedule entities.",
  preview: true
});
var __defProp$1 = Object.defineProperty;
var __decorateClass$1 = (decorators, target, key, kind) => {
  var result = void 0;
  for (var i2 = decorators.length - 1, decorator; i2 >= 0; i2--)
    if (decorator = decorators[i2])
      result = decorator(target, key, result) || result;
  if (result) __defProp$1(target, key, result);
  return result;
};
const _ClimatePresetTimelineEditor = class _ClimatePresetTimelineEditor extends i {
  setConfig(config) {
    this._config = {
      step_size: 15,
      temperature_unit: "°F",
      min_deadband: 2,
      ...config,
      type: "custom:climate-preset-timeline"
    };
  }
  _valueChanged(key, value) {
    if (!this._config) return;
    this._config = {
      ...this._config,
      [key]: value
    };
    this.dispatchEvent(
      new CustomEvent("config-changed", {
        detail: { config: this._config },
        bubbles: true,
        composed: true
      })
    );
  }
  render() {
    var _a2;
    if (!this._config) return b``;
    const climateEntities = Object.keys(((_a2 = this.hass) == null ? void 0 : _a2.states) || {}).filter((entityId) => entityId.startsWith("climate.")).sort();
    return b`
      <div class="editor-container">
        <!-- Target Climate Entity -->
        <div class="form-row">
          <label class="form-label">Climate Space Leader Entity (Required)</label>
          <select
            class="form-select"
            .value=${this._config.entity || ""}
            @change=${(e2) => this._valueChanged("entity", e2.target.value)}
          >
            <option value="">(Select a climate entity...)</option>
            ${climateEntities.map((id) => {
      var _a3, _b, _c, _d;
      const stateObj = (_a3 = this.hass) == null ? void 0 : _a3.states[id];
      const friendlyName = ((_b = stateObj == null ? void 0 : stateObj.attributes) == null ? void 0 : _b.friendly_name) || id;
      const hasPresets = ((_c = stateObj == null ? void 0 : stateObj.attributes) == null ? void 0 : _c.presets) || ((_d = stateObj == null ? void 0 : stateObj.attributes) == null ? void 0 : _d.preset_modes);
      return b`
                <option value=${id} ?selected=${this._config.entity === id}>
                  ${friendlyName} (${id}) ${hasPresets ? "⭐" : ""}
                </option>
              `;
    })}
          </select>
          <span style="font-size: 0.75rem; color: var(--secondary-text-color, #9ca3af);">
            The card will automatically follow this climate entity's active preset mode and display its corresponding schedule.
          </span>
        </div>

        <!-- Card Title -->
        <div class="form-row">
          <label class="form-label">Card Title (optional)</label>
          <input
            type="text"
            class="form-input"
            placeholder="e.g. Climate Preset 1-day Timeline"
            .value=${this._config.title || ""}
            @input=${(e2) => this._valueChanged("title", e2.target.value)}
          />
        </div>

        <!-- Settings Grid -->
        <div class="form-grid">
          <!-- Temperature Unit -->
          <div class="form-row">
            <label class="form-label">Temperature Unit</label>
            <div class="unit-selector">
              <button
                type="button"
                class="unit-btn ${this._config.temperature_unit !== "°C" ? "active" : ""}"
                @click=${() => this._valueChanged("temperature_unit", "°F")}
              >°F</button>
              <button
                type="button"
                class="unit-btn ${this._config.temperature_unit === "°C" ? "active" : ""}"
                @click=${() => this._valueChanged("temperature_unit", "°C")}
              >°C</button>
            </div>
          </div>

          <!-- Time Step Size -->
          <div class="form-row">
            <label class="form-label">Snapping Interval</label>
            <select
              class="form-select"
              .value=${String(this._config.step_size || 15)}
              @change=${(e2) => this._valueChanged("step_size", parseInt(e2.target.value, 10))}
            >
              <option value="15" ?selected=${(this._config.step_size || 15) === 15}>15 Minutes</option>
              <option value="30" ?selected=${this._config.step_size === 30}>30 Minutes</option>
              <option value="60" ?selected=${this._config.step_size === 60}>60 Minutes</option>
            </select>
          </div>
        </div>

        <!-- Minimum Deadband -->
        <div class="form-row">
          <label class="form-label">Min Deadband Between Heat & Cool</label>
          <input
            type="number"
            class="form-input"
            min="0"
            max="15"
            step="1"
            .value=${String(this._config.min_deadband ?? 2)}
            @input=${(e2) => this._valueChanged("min_deadband", parseFloat(e2.target.value) || 0)}
          />
        </div>
      </div>
    `;
  }
};
_ClimatePresetTimelineEditor.styles = i$3`
    :host {
      display: block;
      font-family: var(--paper-font-body1_-_font-family, Roboto, sans-serif);
      color: var(--primary-text-color, #e1e7ec);
    }

    .editor-container {
      display: flex;
      flex-direction: column;
      gap: 16px;
      padding: 12px 4px;
    }

    .form-row {
      display: flex;
      flex-direction: column;
      gap: 6px;
    }

    .form-label {
      font-size: 0.88rem;
      font-weight: 500;
      color: var(--secondary-text-color, #9ca3af);
    }

    .form-input,
    .form-select {
      background: var(--input-idle-line-color, rgba(255, 255, 255, 0.08));
      color: var(--primary-text-color, #ffffff);
      border: 1px solid var(--divider-color, rgba(255, 255, 255, 0.15));
      border-radius: 8px;
      padding: 10px 12px;
      font-size: 0.92rem;
      box-sizing: border-box;
      width: 100%;
      outline: none;
      transition: border-color 0.15s;
    }

    .form-input:focus,
    .form-select:focus {
      border-color: var(--primary-color, #38bdf8);
    }

    .form-select {
      color-scheme: dark;
    }
    .form-select optgroup {
      background: var(--card-background-color, var(--ha-card-background, #1e293b));
      color: var(--secondary-text-color, #9ca3af);
    }
    .form-select option {
      background: var(--card-background-color, var(--ha-card-background, #1e293b));
      color: var(--primary-text-color, #ffffff);
    }

    .form-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 14px;
    }

    .unit-selector {
      display: flex;
      border-radius: 8px;
      overflow: hidden;
      border: 1px solid var(--divider-color, rgba(255, 255, 255, 0.15));
    }

    .unit-btn {
      flex: 1;
      padding: 8px 12px;
      background: rgba(255, 255, 255, 0.05);
      border: none;
      color: var(--secondary-text-color, #9ca3af);
      cursor: pointer;
      font-weight: 600;
      font-size: 0.9rem;
      transition: all 0.15s;
    }

    .unit-btn.active {
      background: var(--primary-color, #38bdf8);
      color: #0f172a;
    }
  `;
let ClimatePresetTimelineEditor = _ClimatePresetTimelineEditor;
__decorateClass$1([
  n2({ attribute: false })
], ClimatePresetTimelineEditor.prototype, "hass");
__decorateClass$1([
  r()
], ClimatePresetTimelineEditor.prototype, "_config");
if (!customElements.get("climate-preset-timeline-editor")) {
  customElements.define("climate-preset-timeline-editor", ClimatePresetTimelineEditor);
}
var __defProp = Object.defineProperty;
var __decorateClass = (decorators, target, key, kind) => {
  var result = void 0;
  for (var i2 = decorators.length - 1, decorator; i2 >= 0; i2--)
    if (decorator = decorators[i2])
      result = decorator(target, key, result) || result;
  if (result) __defProp(target, key, result);
  return result;
};
const _ClimatePresetTimeline = class _ClimatePresetTimeline extends i {
  constructor() {
    super(...arguments);
    this.schedules = [];
    this.activeScheduleId = "";
    this.currentPresetMode = "";
    this.isManual = false;
    this.isEditMode = false;
    this.isYamlSchedule = false;
    this.isForeign = false;
    this.scheduleNotFound = false;
    this._lastLoadedScheduleHash = "";
    this.blocksByDay = {
      monday: [],
      tuesday: [],
      wednesday: [],
      thursday: [],
      friday: [],
      saturday: [],
      sunday: []
    };
    this.selectedDayIndex = ((/* @__PURE__ */ new Date()).getDay() + 6) % 7;
    this.activeEditingBlock = null;
    this.isSaving = false;
    this.dragAction = null;
    this.lastDragEndTime = 0;
  }
  static async getConfigElement() {
    return document.createElement("climate-preset-timeline-editor");
  }
  static getStubConfig() {
    return {
      type: "custom:climate-preset-timeline",
      title: "",
      entity: "",
      temperature_unit: "°F",
      step_size: 15,
      min_deadband: 2
    };
  }
  connectedCallback() {
    super.connectedCallback();
    this._timer = setInterval(() => this.requestUpdate(), 3e4);
    this._unsubscribeSync = subscribeScheduleUpdates(() => {
      this.syncFromHass(true);
    });
  }
  disconnectedCallback() {
    super.disconnectedCallback();
    if (this._timer) {
      clearInterval(this._timer);
      this._timer = void 0;
    }
    if (this._unsubscribeSync) {
      this._unsubscribeSync();
      this._unsubscribeSync = void 0;
    }
    if (this._heartbeatTimer) {
      clearInterval(this._heartbeatTimer);
      this._heartbeatTimer = void 0;
    }
    if (this.isEditMode) {
      this.sendLockSignal(false);
    }
  }
  setConfig(config) {
    if (!config) throw new Error("Invalid configuration");
    this.config = {
      temperature_unit: "°F",
      step_size: 15,
      min_deadband: 2,
      ...config
    };
  }
  getCardSize() {
    return 3;
  }
  willUpdate(changedProps) {
    if (changedProps.has("hass") && this.hass) {
      this.syncFromHass();
    }
  }
  async syncFromHass(forceReload = false) {
    if (!this.hass || this.isSaving || this.dragAction || this.activeEditingBlock) return;
    const list = await fetchScheduleList(this.hass);
    this.schedules = list;
    const targetEntityId = this.config.entity;
    let scheduleEntityId = null;
    if (targetEntityId) {
      const stateObj = this.hass.states[targetEntityId];
      if (targetEntityId.startsWith("climate.")) {
        const attrs = (stateObj == null ? void 0 : stateObj.attributes) || {};
        this.currentPresetMode = attrs.preset_mode || "unknown";
        this.isManual = attrs.preset_mode === "manual";
        if (!this.isManual) {
          const activeSched = attrs.active_schedule;
          const presetsMap = attrs.presets || {};
          if (activeSched && typeof activeSched === "string") {
            scheduleEntityId = activeSched;
          } else if (presetsMap[this.currentPresetMode]) {
            scheduleEntityId = String(presetsMap[this.currentPresetMode]);
          }
        }
      } else if (targetEntityId.startsWith("schedule.")) {
        scheduleEntityId = targetEntityId;
      }
    }
    if (this.isManual) {
      this.activeScheduleId = "";
      this._lastLoadedScheduleHash = "";
      this.isEditMode = false;
      this.isYamlSchedule = false;
      this.isForeign = false;
      this.scheduleNotFound = false;
      this.blocksByDay = {
        monday: [],
        tuesday: [],
        wednesday: [],
        thursday: [],
        friday: [],
        saturday: [],
        sunday: []
      };
      return;
    }
    let item;
    if (scheduleEntityId) {
      item = findScheduleInList(list, scheduleEntityId, this.hass);
    } else if (list.length > 0) {
      item = list[0];
    }
    if (item && !this.isSaving && !this.dragAction && !this.activeEditingBlock) {
      this.isYamlSchedule = false;
      this.isForeign = isForeignSchedule(item);
      this.scheduleNotFound = false;
      if (this.isForeign && this.isEditMode) {
        this.isEditMode = false;
        this.sendLockSignal(false);
      }
      const itemHash = JSON.stringify(item);
      if (forceReload || item.id !== this.activeScheduleId || itemHash !== this._lastLoadedScheduleHash) {
        this.activeScheduleId = item.id;
        this._lastLoadedScheduleHash = itemHash;
        this.blocksByDay = convertToInternalBlocks(item);
      }
    } else if (scheduleEntityId && !item) {
      const fullEntityId = scheduleEntityId.startsWith("schedule.") ? scheduleEntityId : `schedule.${scheduleEntityId}`;
      const stateObj = this.hass.states[fullEntityId];
      if (stateObj) {
        this.isYamlSchedule = true;
        this.isForeign = false;
        this.scheduleNotFound = false;
      } else {
        this.isYamlSchedule = false;
        this.isForeign = false;
        this.scheduleNotFound = true;
      }
      this.activeScheduleId = "";
      this.isEditMode = false;
      this.blocksByDay = {
        monday: [],
        tuesday: [],
        wednesday: [],
        thursday: [],
        friday: [],
        saturday: [],
        sunday: []
      };
    }
  }
  sendLockSignal(acquire) {
    var _a2, _b;
    if (!this.hass || !this.activeScheduleId) return;
    const action = acquire ? "acquire_schedule_lock" : "release_schedule_lock";
    if (!((_b = (_a2 = this.hass.services) == null ? void 0 : _a2.hvac_fusion) == null ? void 0 : _b[action])) return;
    this.hass.callService("hvac_fusion", action, {
      schedule_id: this.activeScheduleId,
      ...acquire ? { duration: 300 } : {}
    });
  }
  toggleEditMode() {
    if (this.isManual || this.isYamlSchedule || this.isForeign || this.scheduleNotFound) return;
    this.isEditMode = !this.isEditMode;
    if (this.isEditMode) {
      this.sendLockSignal(true);
      if (this._heartbeatTimer) clearInterval(this._heartbeatTimer);
      this._heartbeatTimer = setInterval(() => {
        if (this.isEditMode) this.sendLockSignal(true);
      }, 6e4);
    } else {
      if (this._heartbeatTimer) {
        clearInterval(this._heartbeatTimer);
        this._heartbeatTimer = void 0;
      }
      this.sendLockSignal(false);
    }
  }
  get currentDayKey() {
    return DAYS_OF_WEEK[this.selectedDayIndex];
  }
  changeDay(delta) {
    this.selectedDayIndex = (this.selectedDayIndex + delta + 7) % 7;
  }
  // --- Interaction: Dragging & Resizing Horizontally ---
  handleTrackPointerDown(e2) {
    if (!this.isEditMode || this.isManual) return;
    const track = e2.currentTarget;
    const rect = track.getBoundingClientRect();
    const clickX = e2.clientX - rect.left;
    const ratio = Math.max(0, Math.min(1, clickX / rect.width));
    const stepSize = this.config.step_size || 15;
    const clickedMinute = snapMinutes(ratio * 1440, stepSize);
    track.setPointerCapture(e2.pointerId);
    this.dragAction = {
      type: "create",
      initialX: e2.clientX,
      initialMinute: clickedMinute,
      currentMinute: clickedMinute,
      hasDragged: false
    };
  }
  handleBlockClick(e2, block) {
    var _a2;
    e2.stopPropagation();
    if (!this.isEditMode || this.isManual) return;
    if (Date.now() - this.lastDragEndTime < 350 || ((_a2 = this.dragAction) == null ? void 0 : _a2.hasDragged)) return;
    this.activeEditingBlock = block;
  }
  handleResizePointerDown(e2, block, type) {
    e2.stopPropagation();
    if (!this.isEditMode || this.isManual) return;
    e2.target.setPointerCapture(e2.pointerId);
    const blockList = this.blocksByDay[this.currentDayKey];
    let abuttingBlockId;
    if (type === "resize-end") {
      const neighbor = blockList.find((b2) => b2.id !== block.id && b2.startMinutes === block.endMinutes);
      if (neighbor) abuttingBlockId = neighbor.id;
    } else if (type === "resize-start") {
      const neighbor = blockList.find((b2) => b2.id !== block.id && b2.endMinutes === block.startMinutes);
      if (neighbor) abuttingBlockId = neighbor.id;
    }
    this.dragAction = {
      type,
      blockId: block.id,
      abuttingBlockId,
      initialX: e2.clientX,
      initialMinute: type === "resize-start" ? block.startMinutes : block.endMinutes,
      currentMinute: type === "resize-start" ? block.startMinutes : block.endMinutes,
      initialStart: block.startMinutes,
      initialEnd: block.endMinutes,
      hasDragged: false
    };
  }
  handleTrackPointerMove(e2) {
    if (!this.dragAction) return;
    if (Math.abs(e2.clientX - this.dragAction.initialX) > 5) {
      this.dragAction.hasDragged = true;
    }
    const track = e2.currentTarget;
    const rect = track.getBoundingClientRect();
    const currentX = e2.clientX - rect.left;
    const ratio = Math.max(0, Math.min(1, currentX / rect.width));
    const stepSize = this.config.step_size || 15;
    const currentMinute = snapMinutes(ratio * 1440, stepSize);
    const { type, blockId, abuttingBlockId, initialMinute } = this.dragAction;
    const day = this.currentDayKey;
    const blockList = this.blocksByDay[day];
    if (type === "create") {
      if (!this.dragAction.hasDragged) return;
      this.dragAction.currentMinute = currentMinute;
      this.requestUpdate();
      return;
    }
    const currentBlock = blockList.find((b2) => b2.id === blockId);
    if (!currentBlock) return;
    if (type === "resize-start") {
      const nextStart = Math.min(currentBlock.endMinutes - stepSize, Math.max(0, currentMinute));
      this.dragAction.currentMinute = nextStart;
      if (nextStart !== currentBlock.startMinutes) {
        currentBlock.startMinutes = nextStart;
        if (abuttingBlockId) {
          const neighbor = blockList.find((b2) => b2.id === abuttingBlockId);
          if (neighbor) neighbor.endMinutes = nextStart;
        }
      }
      this.requestUpdate();
    } else if (type === "resize-end") {
      const nextEnd = Math.max(currentBlock.startMinutes + stepSize, Math.min(1440, currentMinute));
      this.dragAction.currentMinute = nextEnd;
      if (nextEnd !== currentBlock.endMinutes) {
        currentBlock.endMinutes = nextEnd;
        if (abuttingBlockId) {
          const neighbor = blockList.find((b2) => b2.id === abuttingBlockId);
          if (neighbor) neighbor.startMinutes = nextEnd;
        }
      }
      this.requestUpdate();
    }
  }
  handleTrackPointerUp() {
    if (!this.dragAction) return;
    const { type, initialMinute, hasDragged } = this.dragAction;
    const day = this.currentDayKey;
    if (type === "create") {
      if (!hasDragged) {
        const existing = this.blocksByDay[day].find(
          (b2) => initialMinute >= b2.startMinutes && initialMinute < b2.endMinutes
        );
        if (existing) {
          this.activeEditingBlock = existing;
        } else {
          this.config.step_size || 15;
          const newBlock = {
            id: `${day}_block_${Date.now()}`,
            day,
            startMinutes: initialMinute,
            endMinutes: Math.min(1440, initialMinute + 60),
            hvac_mode: "heat_cool",
            heat_to: 68,
            cool_to: 74
          };
          this.blocksByDay = {
            ...this.blocksByDay,
            [day]: [...this.blocksByDay[day], newBlock].sort((a2, b2) => a2.startMinutes - b2.startMinutes)
          };
          this.activeEditingBlock = newBlock;
        }
      } else {
        const stepSize = this.config.step_size || 15;
        const cur = this.dragAction.currentMinute ?? initialMinute;
        const start = Math.min(initialMinute, cur);
        const end = Math.max(start + stepSize, Math.max(initialMinute, cur));
        this.carveAndInsertBlock(day, start, Math.min(1440, end));
      }
    }
    if (hasDragged) {
      this.lastDragEndTime = Date.now();
    }
    this.dragAction = null;
    this.saveCurrentSchedule();
  }
  carveAndInsertBlock(day, carveStart, carveEnd) {
    const blockList = this.blocksByDay[day];
    const nextBlocks = [];
    const intersected = blockList.find(
      (b2) => b2.startMinutes < carveEnd && b2.endMinutes > carveStart
    );
    for (const b2 of blockList) {
      if (b2.endMinutes <= carveStart || b2.startMinutes >= carveEnd) {
        nextBlocks.push(b2);
      } else if (b2.startMinutes < carveStart && b2.endMinutes > carveEnd) {
        nextBlocks.push({ ...b2, id: `${b2.day}_block_${Date.now()}_l`, endMinutes: carveStart });
        nextBlocks.push({ ...b2, id: `${b2.day}_block_${Date.now()}_r`, startMinutes: carveEnd });
      } else if (b2.startMinutes < carveStart && b2.endMinutes <= carveEnd) {
        nextBlocks.push({ ...b2, endMinutes: carveStart });
      } else if (b2.startMinutes >= carveStart && b2.endMinutes > carveEnd) {
        nextBlocks.push({ ...b2, startMinutes: carveEnd });
      }
    }
    const newBlock = {
      id: `${day}_block_${Date.now()}`,
      day,
      startMinutes: carveStart,
      endMinutes: carveEnd,
      hvac_mode: (intersected == null ? void 0 : intersected.hvac_mode) || "heat_cool",
      heat_to: (intersected == null ? void 0 : intersected.heat_to) ?? 68,
      cool_to: (intersected == null ? void 0 : intersected.cool_to) ?? 74
    };
    nextBlocks.push(newBlock);
    nextBlocks.sort((a2, b2) => a2.startMinutes - b2.startMinutes);
    this.blocksByDay = { ...this.blocksByDay, [day]: nextBlocks };
  }
  handleSaveBlock(e2) {
    const updated = e2.detail.block;
    const day = updated.day;
    this.blocksByDay = {
      ...this.blocksByDay,
      [day]: this.blocksByDay[day].map((b2) => b2.id === updated.id ? updated : b2)
    };
    this.activeEditingBlock = null;
    this.saveCurrentSchedule();
  }
  handleDeleteBlock(e2) {
    const { blockId, day } = e2.detail;
    this.blocksByDay = {
      ...this.blocksByDay,
      [day]: this.blocksByDay[day].filter((b2) => b2.id !== blockId)
    };
    this.activeEditingBlock = null;
    this.saveCurrentSchedule();
  }
  handleSplitBlock(e2) {
    const { blockId, day, splitMinute } = e2.detail;
    const list = this.blocksByDay[day];
    const idx = list.findIndex((b2) => b2.id === blockId);
    if (idx === -1) return;
    const original = list[idx];
    const originalEnd = original.endMinutes;
    original.endMinutes = splitMinute;
    const secondPiece = {
      ...original,
      id: `${day}_block_${Date.now()}`,
      startMinutes: splitMinute,
      endMinutes: originalEnd
    };
    this.blocksByDay = {
      ...this.blocksByDay,
      [day]: [...list, secondPiece].sort((a2, b2) => a2.startMinutes - b2.startMinutes)
    };
    this.activeEditingBlock = null;
    this.saveCurrentSchedule();
  }
  handleCopyBlockTo(e2) {
    const { block, target } = e2.detail;
    const targetDays = target === "weekdays" ? ["monday", "tuesday", "wednesday", "thursday", "friday"] : target === "weekend" ? ["saturday", "sunday"] : DAYS_OF_WEEK;
    const nextBlocks = { ...this.blocksByDay };
    for (const day of targetDays) {
      const copy = {
        ...block,
        id: `${day}_block_${Date.now()}_${Math.random()}`,
        day
      };
      nextBlocks[day] = [
        ...nextBlocks[day].filter(
          (b2) => !(b2.startMinutes < copy.endMinutes && b2.endMinutes > copy.startMinutes)
        ),
        copy
      ].sort((a2, b2) => a2.startMinutes - b2.startMinutes);
    }
    this.blocksByDay = nextBlocks;
    this.activeEditingBlock = null;
    this.saveCurrentSchedule();
  }
  async saveCurrentSchedule() {
    if (!this.hass || !this.activeScheduleId) return;
    this.isSaving = true;
    try {
      const schedule = this.schedules.find((s2) => s2.id === this.activeScheduleId);
      const name = (schedule == null ? void 0 : schedule.name) || this.activeScheduleId;
      const icon = schedule == null ? void 0 : schedule.icon;
      const haDays = convertToHABlocks(this.blocksByDay);
      await updateHASchedule(this.hass, this.activeScheduleId, name, haDays, icon);
      this._lastLoadedScheduleHash = JSON.stringify({ ...schedule, ...haDays, name, icon });
    } catch (err) {
      console.error("[climate-preset-timeline] Failed to save schedule update:", err);
    } finally {
      this.isSaving = false;
    }
  }
  render() {
    var _a2, _b, _c;
    const climateState = this.config.entity ? (_a2 = this.hass) == null ? void 0 : _a2.states[this.config.entity] : void 0;
    const title = this.config.title || ((_b = climateState == null ? void 0 : climateState.attributes) == null ? void 0 : _b.friendly_name) || "Climate Preset 1-day Timeline";
    const dayName = ((_c = DAY_LABELS[this.currentDayKey]) == null ? void 0 : _c.full) || this.currentDayKey;
    const todayIndex = ((/* @__PURE__ */ new Date()).getDay() + 6) % 7;
    const isViewingToday = this.selectedDayIndex === todayIndex;
    const blocks = this.blocksByDay[this.currentDayKey] || [];
    const unit = this.config.temperature_unit || "°F";
    const now = /* @__PURE__ */ new Date();
    const currentMinutes = now.getHours() * 60 + now.getMinutes();
    const nowPct = currentMinutes / 1440 * 100;
    return b`
      <ha-card>
        <!-- Header -->
        <div class="header-row">
          <div class="title-box">
            <h3 class="card-title" title="${title}">${title}</h3>
            ${this.currentPresetMode ? b`
                  <span
                    class="preset-chip ${this.isManual ? "manual" : ""}"
                    title="${this.isManual ? "Manual Mode" : this.currentPresetMode}"
                  >
                    ${this.isManual ? "⚠️ Manual" : `🎯 ${this.currentPresetMode}`}
                  </span>
                ` : ""}
            ${this.isYamlSchedule ? b`<span class="yaml-badge" title="Defined in YAML: edits must be made in configuration.yaml">YAML (Read Only)</span>` : this.isForeign ? b`<span class="yaml-badge" title="Non-HVAC schedule data payloads cannot be edited in this card">Non-HVAC (Read Only)</span>` : ""}
          </div>

          <!-- Controls: Day Navigation + Edit Toggle -->
          <div class="header-controls">
            <!-- Day navigation -->
            <div class="day-nav">
              <button class="nav-btn" @click=${() => this.changeDay(-1)} title="Previous Day">‹</button>
              <span class="day-label">${isViewingToday ? `Today (${dayName.slice(0, 3)})` : dayName}</span>
              <button class="nav-btn" @click=${() => this.changeDay(1)} title="Next Day">›</button>
            </div>

            <!-- Edit mode toggle -->
            <button
              class="edit-toggle-btn ${this.isEditMode ? "active" : ""}"
              @click=${this.toggleEditMode}
              ?disabled=${this.isManual || this.isYamlSchedule || this.isForeign || this.scheduleNotFound}
              title=${this.isManual ? "Manual mode active (no schedule to edit)" : this.isYamlSchedule ? "YAML schedules are read-only" : this.isForeign ? "Non-HVAC schedules are read-only" : this.scheduleNotFound ? "Schedule entity not found" : this.isEditMode ? "Finish editing" : "Enable editing"}
            >
              ${this.isEditMode ? "✓ Done" : "✎ Edit"}
            </button>
          </div>
        </div>

        <!-- Horizontal Timeline Track -->
        <div
          class="timeline-track-wrap ${this.isEditMode ? "editing" : ""}"
          @pointerdown=${this.handleTrackPointerDown}
          @pointermove=${this.handleTrackPointerMove}
          @pointerup=${this.handleTrackPointerUp}
        >
          <!-- Status Overlays -->
          ${this.isManual ? b`
                <div class="manual-overlay">
                  <span>⏸️ Manual Hold Active — No schedule running</span>
                </div>
              ` : this.isYamlSchedule ? b`
                <div class="manual-overlay">
                  <span>📄 YAML Schedule Active — Read-only</span>
                </div>
              ` : this.isForeign ? b`
                <div class="manual-overlay">
                  <span>⚠️ Non-HVAC Schedule Active — Read-only</span>
                </div>
              ` : this.scheduleNotFound ? b`
                <div class="manual-overlay error">
                  <span>⚠️ Schedule entity not found</span>
                </div>
              ` : ""}
          <!-- Grid tick lines every 4 hours -->
          ${[4, 8, 12, 16, 20].map((hour) => {
      const leftPct = hour / 24 * 100;
      return b`<div class="time-grid-line" style="left: ${leftPct}%;"></div>`;
    })}

          <!-- Scheduled Blocks -->
          ${blocks.map((block) => {
      const leftPct = block.startMinutes / 1440 * 100;
      const duration = block.endMinutes - block.startMinutes;
      const widthPct = duration / 1440 * 100;
      const heatColor = getHeatColor(block.heat_to, unit);
      const heatText = getHeatTextColor(block.heat_to, unit);
      const coolColor = getCoolColor(block.cool_to, unit);
      const coolText = getCoolTextColor(block.cool_to, unit);
      const tooltip = block.isGeneric ? `Non-Climate Block: No HVAC targets (${formatTimeDisplay(block.startMinutes)} – ${formatTimeDisplay(block.endMinutes)})` : block.hvac_mode === "heat_cool" ? `Dual: Heat ${block.heat_to}°, Cool ${block.cool_to}° (${formatTimeDisplay(block.startMinutes)} – ${formatTimeDisplay(block.endMinutes)})` : `${block.hvac_mode} (${formatTimeDisplay(block.startMinutes)} – ${formatTimeDisplay(block.endMinutes)})`;
      return b`
              <div
                class="timeline-block"
                style="left: ${leftPct}%; width: ${widthPct}%;"
                title=${tooltip}
                @click=${(e2) => this.handleBlockClick(e2, block)}
              >
                ${block.isGeneric ? b`
                      <div class="band-generic">
                        ${widthPct > 8 ? "No HVAC" : ""}
                      </div>
                    ` : block.hvac_mode === "heat_cool" ? b`
                      <div class="band-cool" style="background-color: ${coolColor}; color: ${coolText};">
                        ${widthPct > 5 ? `${block.cool_to}°` : ""}
                      </div>
                      <div class="band-heat" style="background-color: ${heatColor}; color: ${heatText};">
                        ${widthPct > 5 ? `${block.heat_to}°` : ""}
                      </div>
                    ` : block.hvac_mode === "heat" ? b`
                      <div class="band-heat" style="background-color: ${heatColor}; color: ${heatText}; flex: 1;">
                        ${block.heat_to}°
                      </div>
                    ` : block.hvac_mode === "cool" ? b`
                      <div class="band-cool" style="background-color: ${coolColor}; color: ${coolText}; flex: 1;">
                        ${block.cool_to}°
                      </div>
                    ` : b`<div style="flex: 1; background: #27272a;"></div>`}

                <!-- Resize handles -->
                <div
                  class="h-resize-handle left"
                  @click=${(e2) => e2.stopPropagation()}
                  @pointerdown=${(e2) => this.handleResizePointerDown(e2, block, "resize-start")}
                ></div>
                <div
                  class="h-resize-handle right"
                  @click=${(e2) => e2.stopPropagation()}
                  @pointerdown=${(e2) => this.handleResizePointerDown(e2, block, "resize-end")}
                ></div>
              </div>
            `;
    })}

          <!-- Carve preview overlay -->
          ${this.dragAction && this.dragAction.type === "create" && this.dragAction.hasDragged ? (() => {
      const step = this.config.step_size || 15;
      const cur = this.dragAction.currentMinute ?? this.dragAction.initialMinute;
      const start = Math.min(this.dragAction.initialMinute, cur);
      const end = Math.min(1440, Math.max(start + step, Math.max(this.dragAction.initialMinute, cur)));
      const leftPct = start / 1440 * 100;
      const widthPct = (end - start) / 1440 * 100;
      return b`
                  <div class="carve-overlay" style="left: ${leftPct}%; width: ${widthPct}%;">
                    ${formatTimeDisplay(start)} – ${formatTimeDisplay(end)}
                  </div>
                `;
    })() : ""}

          <!-- Floating drag resize guide -->
          ${this.dragAction && (this.dragAction.type === "resize-start" || this.dragAction.type === "resize-end") && this.dragAction.currentMinute !== void 0 ? (() => {
      const leftPct = this.dragAction.currentMinute / 1440 * 100;
      return b`
                  <div class="drag-h-indicator" style="left: ${leftPct}%;">
                    <div class="drag-h-line"></div>
                    <div class="drag-h-pill">${formatTimeDisplay(this.dragAction.currentMinute)}</div>
                  </div>
                `;
    })() : ""}

          <!-- Red "NOW" needle if viewing today -->
          ${isViewingToday ? b`<div class="now-needle" style="left: ${nowPct}%;" title="Current Time"></div>` : ""}
        </div>

        <!-- Horizontal Time Axis Labels -->
        <div class="time-axis-horizontal">
          <span>00:00</span>
          <span>04:00</span>
          <span>08:00</span>
          <span>12:00</span>
          <span>16:00</span>
          <span>20:00</span>
          <span>24:00</span>
        </div>

        <!-- Edit Dialog -->
        ${this.activeEditingBlock ? b`
              <preset-dialog
                .block=${this.activeEditingBlock}
                .temperatureUnit=${this.config.temperature_unit || "°F"}
                .minDeadband=${this.config.min_deadband || 2}
                .minTemp=${45}
                .maxTemp=${85}
                @save-block=${this.handleSaveBlock}
                @delete-block=${this.handleDeleteBlock}
                @split-block=${this.handleSplitBlock}
                @copy-block-to=${this.handleCopyBlockTo}
                @close-dialog=${() => this.activeEditingBlock = null}
              ></preset-dialog>
            ` : ""}
      </ha-card>
    `;
  }
};
_ClimatePresetTimeline.styles = i$3`
    :host {
      display: block;
      font-family: var(--paper-font-body1_-_font-family, Roboto, sans-serif);
      color: var(--primary-text-color, #e1e7ec);
      user-select: none;
      -webkit-user-select: none;
    }

    ha-card {
      background: var(--ha-card-background, var(--card-background-color, #181c24));
      border-radius: var(--ha-card-border-radius, 16px);
      border: 1px solid var(--divider-color, rgba(255, 255, 255, 0.08));
      padding: 16px;
      overflow: hidden;
      display: flex;
      flex-direction: column;
      gap: 12px;
    }

    /* Header */
    .header-row {
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: nowrap;
      gap: 8px;
      min-width: 0;
    }

    .title-box {
      display: flex;
      align-items: center;
      gap: 8px;
      min-width: 0;
      flex: 1 1 auto;
      overflow: hidden;
    }

    .card-title {
      font-size: 1.1rem;
      font-weight: 600;
      color: var(--primary-text-color, #ffffff);
      margin: 0;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
      min-width: 0;
      flex-shrink: 1;
    }

    .preset-chip {
      font-size: 0.75rem;
      font-weight: 600;
      padding: 3px 9px;
      border-radius: 12px;
      background: rgba(56, 189, 248, 0.15);
      color: var(--primary-color, #38bdf8);
      border: 1px solid rgba(56, 189, 248, 0.3);
      text-transform: capitalize;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
      max-width: 160px;
      flex-shrink: 2;
    }
    .preset-chip.manual {
      background: rgba(234, 179, 8, 0.15);
      color: #eab308;
      border-color: rgba(234, 179, 8, 0.3);
    }
    .yaml-badge {
      font-size: 0.72rem;
      padding: 3px 8px;
      border-radius: 6px;
      background: rgba(234, 179, 8, 0.15);
      color: #eab308;
      border: 1px solid rgba(234, 179, 8, 0.3);
      white-space: nowrap;
      flex-shrink: 0;
    }

    .header-controls {
      display: flex;
      align-items: center;
      gap: 6px;
      flex-shrink: 0;
    }

    /* Day Navigation */
    .day-nav {
      display: flex;
      align-items: center;
      gap: 2px;
      background: rgba(255, 255, 255, 0.05);
      border-radius: 8px;
      padding: 2px 4px;
      flex-shrink: 0;
    }

    .nav-btn {
      background: transparent;
      border: none;
      color: var(--secondary-text-color, #9ca3af);
      font-size: 1rem;
      cursor: pointer;
      padding: 2px 6px;
      border-radius: 4px;
      transition: all 0.15s;
    }
    .nav-btn:hover {
      background: rgba(255, 255, 255, 0.1);
      color: #fff;
    }

    .day-label {
      font-size: 0.82rem;
      font-weight: 600;
      padding: 0 4px;
      min-width: 70px;
      text-align: center;
      white-space: nowrap;
    }

    .edit-toggle-btn {
      background: rgba(255, 255, 255, 0.06);
      border: 1px solid rgba(255, 255, 255, 0.12);
      color: var(--secondary-text-color, #9ca3af);
      font-size: 0.78rem;
      font-weight: 600;
      padding: 4px 10px;
      border-radius: 6px;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 5px;
      transition: all 0.15s ease-in-out;
    }
    .edit-toggle-btn:hover:not(:disabled) {
      background: rgba(255, 255, 255, 0.12);
      color: #fff;
    }
    .edit-toggle-btn.active {
      background: rgba(56, 189, 248, 0.18);
      border-color: #38bdf8;
      color: #38bdf8;
    }
    .edit-toggle-btn:disabled {
      opacity: 0.4;
      cursor: not-allowed;
    }

    /* Horizontal Track Container */
    .timeline-track-wrap {
      position: relative;
      width: 100%;
      height: 64px;
      background: rgba(0, 0, 0, 0.3);
      border-radius: 10px;
      border: 1px solid rgba(255, 255, 255, 0.08);
      overflow: hidden;
      touch-action: none;
      cursor: default;
      transition: border-color 0.2s;
    }
    .timeline-track-wrap.editing {
      cursor: crosshair;
      border-color: rgba(56, 189, 248, 0.45);
    }
    .timeline-track-wrap.editing .timeline-block {
      cursor: pointer;
    }
    .timeline-track-wrap:not(.editing) .timeline-block {
      cursor: default;
    }
    .timeline-track-wrap:not(.editing) .h-resize-handle {
      display: none;
    }

    .manual-overlay {
      position: absolute;
      top: 0;
      bottom: 0;
      left: 0;
      right: 0;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
      background: rgba(24, 28, 36, 0.72);
      color: #eab308;
      font-size: 0.85rem;
      font-weight: 500;
      pointer-events: none;
      z-index: 15;
    }
    .manual-overlay.error {
      color: #f87171;
    }

    /* Horizontal Grid Ticks (every 4 hours) */
    .time-grid-line {
      position: absolute;
      top: 0;
      bottom: 0;
      width: 1px;
      background: rgba(255, 255, 255, 0.05);
      pointer-events: none;
    }

    /* Blocks */
    .timeline-block {
      position: absolute;
      top: 2px;
      bottom: 2px;
      border-radius: 6px;
      overflow: hidden;
      cursor: pointer;
      box-shadow: 0 2px 5px rgba(0, 0, 0, 0.4);
      border: 1px solid rgba(255, 255, 255, 0.15);
      box-sizing: border-box;
      display: flex;
      flex-direction: column;
      transition: border-color 0.15s;
    }
    .timeline-block:hover {
      border-color: rgba(255, 255, 255, 0.5);
      z-index: 10;
    }

    .band-cool,
    .band-heat {
      flex: 1;
      width: 100%;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 0.72rem;
      font-weight: 700;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      min-height: 0;
    }

    .band-generic {
      flex: 1;
      width: 100%;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 0.70rem;
      font-weight: 600;
      color: #cbd5e1;
      background: rgba(100, 116, 139, 0.35);
      border: 1px dashed rgba(148, 163, 184, 0.7);
      text-transform: uppercase;
      letter-spacing: 0.03em;
      min-height: 0;
    }

    /* Horizontal Resize Handles (Left / Right edges) */
    .h-resize-handle {
      position: absolute;
      top: 0;
      bottom: 0;
      width: 10px;
      z-index: 20;
      cursor: ew-resize;
    }
    .h-resize-handle.left {
      left: 0;
    }
    .h-resize-handle.right {
      right: 0;
    }
    .h-resize-handle:hover {
      background: rgba(255, 255, 255, 0.25);
    }

    /* NOW Needle */
    .now-needle {
      position: absolute;
      top: 0;
      bottom: 0;
      width: 2px;
      background: #ffffff;
      box-shadow: 0 0 1px 1px rgba(0, 0, 0, 0.7), 0 0 6px 1px rgba(244, 63, 94, 0.85);
      z-index: 30;
      pointer-events: none;
    }
    .now-needle::after {
      content: '';
      position: absolute;
      top: 0;
      left: 50%;
      transform: translateX(-50%);
      width: 0;
      height: 0;
      border-left: 4px solid transparent;
      border-right: 4px solid transparent;
      border-top: 5px solid #ffffff;
      filter: drop-shadow(0 0 2px rgba(244, 63, 94, 0.9));
    }

    /* Time Axis Labels (Under track) */
    .time-axis-horizontal {
      display: flex;
      justify-content: space-between;
      font-size: 0.72rem;
      color: var(--secondary-text-color, #71717a);
      padding: 0 2px;
    }

    /* Carve preview overlay */
    .carve-overlay {
      position: absolute;
      top: 2px;
      bottom: 2px;
      border: 2px dashed var(--primary-color, #38bdf8);
      background: rgba(56, 189, 248, 0.28);
      border-radius: 6px;
      pointer-events: none;
      z-index: 25;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 0.72rem;
      font-weight: 700;
      color: #fff;
    }

    /* Floating drag time badge */
    .drag-h-indicator {
      position: absolute;
      top: -8px;
      bottom: -8px;
      width: 0;
      pointer-events: none;
      z-index: 50;
      display: flex;
      flex-direction: column;
      align-items: center;
      transform: translateX(-50%);
    }

    .drag-h-line {
      position: absolute;
      top: 0;
      bottom: 0;
      width: 2px;
      background: var(--primary-color, #38bdf8);
      box-shadow: 0 0 8px rgba(56, 189, 248, 0.9);
    }

    .drag-h-pill {
      position: relative;
      top: -24px;
      background: #090d16;
      color: #38bdf8;
      border: 1.5px solid #38bdf8;
      padding: 2px 7px;
      border-radius: 6px;
      font-size: 0.74rem;
      font-weight: 700;
      box-shadow: 0 4px 10px rgba(0, 0, 0, 0.8);
      white-space: nowrap;
    }
  `;
let ClimatePresetTimeline = _ClimatePresetTimeline;
__decorateClass([
  n2({ attribute: false })
], ClimatePresetTimeline.prototype, "hass");
__decorateClass([
  r()
], ClimatePresetTimeline.prototype, "config");
__decorateClass([
  r()
], ClimatePresetTimeline.prototype, "schedules");
__decorateClass([
  r()
], ClimatePresetTimeline.prototype, "activeScheduleId");
__decorateClass([
  r()
], ClimatePresetTimeline.prototype, "currentPresetMode");
__decorateClass([
  r()
], ClimatePresetTimeline.prototype, "isManual");
__decorateClass([
  r()
], ClimatePresetTimeline.prototype, "isEditMode");
__decorateClass([
  r()
], ClimatePresetTimeline.prototype, "isYamlSchedule");
__decorateClass([
  r()
], ClimatePresetTimeline.prototype, "isForeign");
__decorateClass([
  r()
], ClimatePresetTimeline.prototype, "scheduleNotFound");
__decorateClass([
  r()
], ClimatePresetTimeline.prototype, "blocksByDay");
__decorateClass([
  r()
], ClimatePresetTimeline.prototype, "selectedDayIndex");
__decorateClass([
  r()
], ClimatePresetTimeline.prototype, "activeEditingBlock");
__decorateClass([
  r()
], ClimatePresetTimeline.prototype, "isSaving");
if (!customElements.get("climate-preset-timeline")) {
  customElements.define("climate-preset-timeline", ClimatePresetTimeline);
}
window.customCards = window.customCards || [];
window.customCards.push({
  type: "climate-preset-timeline",
  name: "Climate Preset 1-day Timeline",
  description: "Single-day horizontal timeline tracker bound to a space climate preset schedule.",
  preview: true
});
export {
  DAYS_OF_WEEK,
  DAY_LABELS
};
//# sourceMappingURL=hvac-fusion-cards.js.map
