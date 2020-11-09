(this["webpackJsonphue-emulator-ui"] =
  this["webpackJsonphue-emulator-ui"] || []).push([
  [0],
  {
    239: function (e, t, a) {
      e.exports = a(484);
    },
    484: function (e, t, a) {
      "use strict";
      a.r(t),
        a.d(t, "httpPutRequest", function () {
          return ve;
        });
      var n = a(71),
        r = a.n(n),
        o = a(139),
        c = a(40),
        l = a(0),
        i = a.n(l),
        u = a(9),
        s = a(41),
        m = a(25),
        d = a(91),
        p = a.n(d),
        h = a(92),
        f = a(229),
        b = a(57),
        E = a(534),
        g = a(521),
        w = a(542),
        v = a(527),
        O = a(528),
        j = a(535),
        x = a(536),
        y = a(524),
        C = a(61),
        k = a(537),
        M = a(540),
        N = a(538),
        S = a(541),
        I = a(93),
        L = a.n(I),
        B = a(216),
        P = a.n(B),
        T = a(72),
        D = a.n(T),
        F = a(217),
        z = a.n(F),
        G = a(526),
        H = a(525),
        _ = a(218),
        J = a.n(_),
        A = a(529),
        R = a(532),
        U = a(531),
        V = a(530),
        q = a(533),
        K = a(539),
        W = a(219),
        Y = a.n(W),
        Q = a(220),
        X = a.n(Q),
        Z = a(221),
        $ = a.n(Z),
        ee = a(222),
        te = a(141);
      a(472);
      function ae(e, t, a) {
        void 0 === a && (a = 254);
        var n = 1 - e - t,
          r = (a / 254).toFixed(2),
          o = (r / t) * e,
          c = (r / t) * n,
          l = 1.656492 * o - 0.354851 * r - 0.255038 * c,
          i = 0.707196 * -o + 1.655397 * r + 0.036152 * c,
          u = 0.051713 * o - 0.121364 * r + 1.01153 * c;
        return (
          l > u && l > i && l > 1
            ? ((i /= l), (u /= l), (l = 1))
            : i > u && i > l && i > 1
            ? ((l /= i), (u /= i), (i = 1))
            : u > l && u > i && u > 1 && ((l /= u), (i /= u), (u = 1)),
          (l =
            l <= 0.0031308 ? 12.92 * l : 1.055 * Math.pow(l, 1 / 2.4) - 0.055),
          (i =
            i <= 0.0031308 ? 12.92 * i : 1.055 * Math.pow(i, 1 / 2.4) - 0.055),
          (u =
            u <= 0.0031308 ? 12.92 * u : 1.055 * Math.pow(u, 1 / 2.4) - 0.055),
          (l = Math.round(255 * l)),
          (i = Math.round(255 * i)),
          (u = Math.round(255 * u)),
          isNaN(l) && (l = 0),
          isNaN(i) && (i = 0),
          isNaN(u) && (u = 0),
          "#" + (16777216 + u + 256 * i + 65536 * l).toString(16).substr(1)
        );
      }
      function ne(e) {
        var t,
          a,
          n,
          r = 2e4 / e;
        return (
          r <= 66
            ? ((t = 255),
              (a = 99.4708025861 * Math.log(r) - 161.1195681661),
              (n =
                r <= 19
                  ? 0
                  : 138.5177312231 * Math.log(r - 10) - 305.0447927307))
            : ((t = 329.698727446 * Math.pow(r - 60, -0.1332047592)),
              (a = 288.1221695283 * Math.pow(r - 60, -0.0755148492)),
              (n = 255)),
          (t = t > 255 ? 255 : t),
          (a = a > 255 ? 255 : a),
          (n = n > 255 ? 255 : n),
          "#" +
            (
              16777216 +
              parseInt(n, 10) +
              256 * parseInt(a, 10) +
              65536 * parseInt(t, 10)
            )
              .toString(16)
              .substr(1)
        );
      }
      function re(e, t, a) {
        var n =
            0.664511 *
              (e =
                e > 0.04045 ? Math.pow((e + 0.055) / 1.055, 2.4) : e / 12.92) +
            0.154324 *
              (t =
                t > 0.04045 ? Math.pow((t + 0.055) / 1.055, 2.4) : t / 12.92) +
            0.162028 *
              (a =
                a > 0.04045 ? Math.pow((a + 0.055) / 1.055, 2.4) : a / 12.92),
          r = 0.283881 * e + 0.668433 * t + 0.047685 * a,
          o = 88e-6 * e + 0.07231 * t + 0.986039 * a,
          c = (n / (n + r + o)).toFixed(4),
          l = (r / (n + r + o)).toFixed(4);
        return (
          isNaN(c) && (c = 0),
          isNaN(l) && (l = 0),
          [parseFloat(c), parseFloat(l)]
        );
      }
      var oe = {
        ct: function (e) {
          return ne(e.state.ct);
        },
        xy: function (e) {
          var t = e.state,
            a = t.xy,
            n = void 0 === a ? [0, 0] : a,
            r = t.bri,
            o = void 0 === r ? 0 : r;
          return ae(n[0], n[1], o);
        },
      };
      function ce() {
        var e = Object(c.a)([
          "\n  margin-top: -0.5em !important;\n  margin-bottom: -0.5em !important;\n",
        ]);
        return (
          (ce = function () {
            return e;
          }),
          e
        );
      }
      function le() {
        var e = Object(c.a)([
          "\n  width: 500px;\n  max-width: calc(100vw - 80px);\n",
        ]);
        return (
          (le = function () {
            return e;
          }),
          e
        );
      }
      function ie() {
        var e = Object(c.a)([
          "\n  .rc-slider-rail {\n    background-image: linear-gradient(\n      to right,\n      #5373d8,\n      #c7e1fd,\n      #fae3a8,\n      #c14334\n    );\n  }\n  .rc-slider-track {\n    background: transparent;\n  }\n",
        ]);
        return (
          (ie = function () {
            return e;
          }),
          e
        );
      }
      var ue = Object(s.b)(te.a)(ie()),
        se = Object(s.b)(g.a)(le()),
        me = Object(s.b)(y.a)(ce()),
        de = Object(m.a)(
          Object(m.d)("isDialogOpen", "setDialogOpen", !1),
          Object(m.d)("selectedLight", "setSelectedLight", void 0),
          Object(m.d)(
            "smallScreen",
            "setSmallScreen",
            window.matchMedia("(max-width: 800px)").matches
          ),
          Object(m.b)({
            componentDidMount: function () {
              var e = this;
              window.addEventListener(
                "resize",
                p()(500)(function () {
                  return e.props.setSmallScreen(
                    window.matchMedia("(max-width: 800px)").matches
                  );
                })
              );
            },
          })
        )(function (e) {
          var t = e.setColorTemperature,
            a = e.setColor,
            n = e.setBrightness,
            r = e.setState,
            o = e.room,
            c = e.lights,
            u = e.isDialogOpen,
            s = e.setDialogOpen,
            m = e.selectedLight,
            d = e.setSelectedLight,
            p = e.smallScreen;
          return i.a.createElement(
            g.a,
            {
              subheader: i.a.createElement(
                H.a,
                null,
                o.name,
                i.a.createElement(
                  G.a,
                  null,
                  i.a.createElement(M.a, {
                    checked: o.state.any_on,
                    onChange: function () {
                      return r(o, !o.state.any_on);
                    },
                  })
                )
              ),
            },
            o.lights
              .filter(function (e) {
                return Boolean(c[e]);
              })
              .map(function (e) {
                return Object(h.a)({}, c[e], { id: e });
              })
              .map(function (e) {
                return i.a.createElement(
                  w.a,
                  { key: e.id },
                  i.a.createElement(
                    v.a,
                    null,
                    i.a.createElement(
                      me,
                      {
                        onClick: function () {
                          s(!0), d(e);
                        },
                      },
                      e.state.on
                        ? i.a.createElement(L.a, {
                            color:
                              "ct" === e.state.colormode
                                ? ne(e.state.ct)
                                : "xy" === e.state.colormode
                                ? ae(e.state.xy[0], e.state.xy[1], e.state.bri)
                                : "#fcf794",
                          })
                        : i.a.createElement(J.a, null)
                    )
                  ),
                  i.a.createElement(O.a, { primary: e.name }),
                  i.a.createElement(
                    G.a,
                    null,
                    i.a.createElement(M.a, {
                      checked: e.state.on,
                      onChange: function () {
                        return r(e, !e.state.on);
                      },
                    })
                  )
                );
              }),
            i.a.createElement(
              A.a,
              {
                fullScreen: p,
                open: u,
                onClose: function () {
                  return s(!1);
                },
                "aria-labelledby": "alert-dialog-title",
                "aria-describedby": "alert-dialog-description",
              },
              m
                ? i.a.createElement(
                    l.Fragment,
                    null,
                    i.a.createElement(
                      V.a,
                      { id: "alert-dialog-title" },
                      o.name,
                      " ",
                      m.name
                    ),
                    i.a.createElement(
                      U.a,
                      null,
                      i.a.createElement(
                        se,
                        null,
                        "bri" in m.state &&
                          i.a.createElement(
                            w.a,
                            null,
                            i.a.createElement(
                              K.a,
                              null,
                              i.a.createElement(Y.a, { color: "white" })
                            ),
                            i.a.createElement(O.a, {
                              primary: i.a.createElement(te.a, {
                                min: 0,
                                max: 255,
                                defaultValue: m.state.on ? m.state.bri : 0,
                                onChange: function (e) {
                                  return n(m, e);
                                },
                              }),
                              secondary: "Brightness",
                            })
                          ),
                        "ct" in m.state &&
                          i.a.createElement(
                            w.a,
                            null,
                            i.a.createElement(
                              K.a,
                              null,
                              i.a.createElement(X.a, { color: "white" })
                            ),
                            i.a.createElement(O.a, {
                              primary: i.a.createElement(ue, {
                                min: 153,
                                max: 500,
                                defaultValue: Math.max(
                                  153,
                                  Math.min(m.state.ct, 500)
                                ),
                                onChange: function (e) {
                                  return t(m, e);
                                },
                              }),
                              secondary: "Temperature",
                            })
                          ),
                        ("xy" in m.state || "hue" in m.state) &&
                          i.a.createElement(
                            w.a,
                            null,
                            i.a.createElement(
                              K.a,
                              null,
                              i.a.createElement($.a, { color: "white" })
                            ),
                            i.a.createElement(O.a, {
                              primary: i.a.createElement(ee.HuePicker, {
                                width: "100%",
                                color: ae(
                                  m.state.xy[0],
                                  m.state.xy[1],
                                  m.state.bri
                                ),
                                defaultColor: oe[m.state.colormode](m),
                                onChange: function (e) {
                                  return a(m, e);
                                },
                              }),
                              secondary: "Color",
                            })
                          )
                      )
                    ),
                    i.a.createElement(
                      R.a,
                      null,
                      i.a.createElement(
                        q.a,
                        {
                          onClick: function () {
                            return s(!1);
                          },
                          color: "primary",
                          autoFocus: !0,
                        },
                        "Close"
                      )
                    )
                  )
                : i.a.createElement("span", null)
            )
          );
        });
      function pe() {
        var e = Object(c.a)(["\n  flex: 1;\n"]);
        return (
          (pe = function () {
            return e;
          }),
          e
        );
      }
      var he = Object(s.a)(pe()),
        fe = Object(E.a)(function (e) {
          return {
            root: {
              flexGrow: 1,
              height: "100vh",
              zIndex: 1,
              overflow: "hidden",
              position: "relative",
              display: "flex",
            },
            appBar: Object(b.a)(
              { zIndex: e.zIndex.drawer + 1, marginLeft: 240 },
              e.breakpoints.up("md"),
              { width: "calc(100% - ".concat(240, "px)") }
            ),
            navIconHide: Object(b.a)({}, e.breakpoints.up("md"), {
              display: "none",
            }),
            toolbar: e.mixins.toolbar,
            drawerPaper: Object(b.a)({ width: 240 }, e.breakpoints.up("md"), {
              position: "relative",
            }),
            content: {
              flexGrow: 1,
              overflow: "auto",
              backgroundColor: e.palette.background.default,
              padding: 3 * e.spacing.unit,
              minWidth: 0,
            },
          };
        }),
        be = function (e) {
          return Object.values(e).some(function (e) {
            return e.state.any_on;
          });
        },
        Ee = i.a.createElement(
          g.a,
          { component: "nav" },
          i.a.createElement(
            w.a,
            { button: !0, href: "/", component: "a" },
            i.a.createElement(v.a, null, i.a.createElement(L.a, null)),
            i.a.createElement(O.a, null, "Lights control")
          ),
          i.a.createElement(
            w.a,
            { button: !0, href: "/hue/linkbutton", component: "a" },
            i.a.createElement(v.a, null, i.a.createElement(P.a, null)),
            i.a.createElement(O.a, null, "Link device")
          ),
          i.a.createElement(
            w.a,
            { button: !0, href: "/hue", component: "a" },
            i.a.createElement(v.a, null, i.a.createElement(D.a, null)),
            i.a.createElement(O.a, null, "Import from bridge")
          ),
          i.a.createElement(
            w.a,
            { button: !0, href: "/tradfri", component: "a" },
            i.a.createElement(v.a, null, i.a.createElement(D.a, null)),
            i.a.createElement(O.a, null, "Import from Tradfri")
          ),
          i.a.createElement(
            w.a,
            { button: !0, href: "/deconz", component: "a" },
            i.a.createElement(v.a, null, i.a.createElement(D.a, null)),
            i.a.createElement(O.a, null, "Deconz")
          ),
          i.a.createElement(
            w.a,
            { button: !0, href: "/milight", component: "a" },
            i.a.createElement(v.a, null, i.a.createElement(D.a, null)),
            i.a.createElement(O.a, null, "Add MiLight Bulb")
          )
        ),
        ge = function (e) {
          var t = e.groups,
            a = e.lights,
            n = e.onColorTemperatureChange,
            r = e.onColorChange,
            o = e.onBrightnessChange,
            c = e.onStateChange,
            u = e.onGlobalStateChange,
            s = fe(),
            m = Object(l.useState)({ drawer: !1 }),
            d = Object(f.a)(m, 2),
            p = d[0],
            b = d[1];
          return i.a.createElement(
            "div",
            { className: s.root },
            i.a.createElement(
              j.a,
              { position: "absolute", className: s.appBar },
              i.a.createElement(
                x.a,
                null,
                i.a.createElement(
                  y.a,
                  {
                    onClick: function () {
                      return b({ drawer: !0 });
                    },
                    className: s.navIconHide,
                  },
                  i.a.createElement(z.a, { color: "white" })
                ),
                i.a.createElement(
                  C.a,
                  { variant: "title", color: "inherit", className: he },
                  "Hue Emulator"
                ),
                i.a.createElement(k.a, {
                  control: i.a.createElement(M.a, {
                    checked: be(t),
                    onChange: function () {
                      return u(!be(t));
                    },
                  }),
                  label: i.a.createElement(
                    "span",
                    { style: { color: "white" } },
                    "Turn all ",
                    be(t) ? "off" : "on"
                  ),
                })
              )
            ),
            i.a.createElement(
              N.a,
              { mdUp: !0 },
              i.a.createElement(
                S.a,
                {
                  variant: "temporary",
                  open: p.drawer,
                  onClose: function () {
                    return b({ drawer: !1 });
                  },
                  classes: { paper: s.drawerPaper },
                  ModalProps: { keepMounted: !0 },
                },
                i.a.createElement("div", { className: s.toolbar }),
                Ee
              )
            ),
            i.a.createElement(
              N.a,
              { smDown: !0, implementation: "css" },
              i.a.createElement(
                S.a,
                {
                  variant: "permanent",
                  open: !0,
                  onClose: function () {
                    return b({ drawer: !1 });
                  },
                  classes: { paper: s.drawerPaper },
                },
                i.a.createElement("div", { className: s.toolbar }),
                Ee
              )
            ),
            i.a.createElement(
              "main",
              { className: s.content },
              i.a.createElement("div", { className: s.toolbar }),
              Object.keys(t)
                .map(function (e) {
                  return Object(h.a)({}, t[e], { id: e });
                })
                .map(function (e) {
                  return i.a.createElement(de, {
                    key: e.id,
                    room: e,
                    lights: a,
                    setColorTemperature: n,
                    setColor: r,
                    setBrightness: o,
                    setState: c,
                  });
                })
            )
          );
        };
      function we() {
        var e = Object(c.a)(["\n  html, body {\n    margin: 0;\n  }\n"]);
        return (
          (we = function () {
            return e;
          }),
          e
        );
      }
      function ve(e, t) {
        return fetch(e, {
          method: "PUT",
          mode: "cors",
          body: JSON.stringify(t),
          headers: { "Content-Type": "application/json" },
        })
          .then(function (e) {
            return e;
          })
          .catch(function (e) {
            return console.error(e.message);
          });
      }
      Object(s.c)(we());
      var Oe = window.config.API_KEY,
        je = p()(1e3),
        xe = Object(m.a)(
          Object(m.d)("groups", "setGroups", {}),
          Object(m.d)("lights", "setLights", {}),
          Object(m.c)({
            onColorTemperatureChange: je(function (e, t) {
              return ve("/api/".concat(Oe, "/lights/").concat(e.id, "/state"), {
                ct: t,
              });
            }),
            onColorChange: je(function (e, t) {
              return ve("/api/".concat(Oe, "/lights/").concat(e.id, "/state"), {
                xy: re(t.rgb.r, t.rgb.g, t.rgb.b),
              });
            }),
            onBrightnessChange: je(function (e, t) {
              return ve("/api/".concat(Oe, "/lights/").concat(e.id, "/state"), {
                bri: t,
              });
            }),
            onStateChange: function (e, t) {
              return ve(
                "/api/"
                  .concat(Oe, "/")
                  .concat(
                    "Room" === e.type
                      ? "groups/" + e.id + "/action"
                      : "lights/" + e.id + "/state"
                  ),
                { on: t }
              );
            },
            onGlobalStateChange: function (e) {
              return ve("/api/".concat(Oe, "/groups/0/action"), { on: e });
            },
          }),
          Object(m.b)({
            componentDidMount: function () {
              var e = this;
              return Object(o.a)(
                r.a.mark(function t() {
                  return r.a.wrap(function (t) {
                    for (;;)
                      switch ((t.prev = t.next)) {
                        case 0:
                          setInterval(
                            Object(o.a)(
                              r.a.mark(function t() {
                                var a, n;
                                return r.a.wrap(function (t) {
                                  for (;;)
                                    switch ((t.prev = t.next)) {
                                      case 0:
                                        return (
                                          (t.next = 2),
                                          Promise.all([
                                            fetch(
                                              "/api/".concat(Oe, "/groups")
                                            ),
                                            fetch(
                                              "/api/".concat(Oe, "/lights")
                                            ),
                                          ])
                                        );
                                      case 2:
                                        return (
                                          (a = t.sent),
                                          (t.next = 5),
                                          Promise.all([
                                            a[0].json(),
                                            a[1].json(),
                                          ])
                                        );
                                      case 5:
                                        (n = t.sent),
                                          e.props.setGroups(n[0]),
                                          e.props.setLights(n[1]);
                                      case 8:
                                      case "end":
                                        return t.stop();
                                    }
                                }, t);
                              })
                            ),
                            1e3
                          );
                        case 1:
                        case "end":
                          return t.stop();
                      }
                  }, t);
                })
              )();
            },
          })
        )(ge);
      Object(u.render)(
        i.a.createElement(xe, null),
        document.getElementById("root")
      );
    },
  },
  [[239, 1, 2]],
]);
//# sourceMappingURL=main.f9be324d.chunk.js.map
