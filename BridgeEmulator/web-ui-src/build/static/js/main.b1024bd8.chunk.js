(window.webpackJsonp = window.webpackJsonp || []).push([
  [0],
  {
    304: function(e, t, n) {
      e.exports = n(686);
    },
    686: function(e, t, n) {
      "use strict";
      n.r(t);
      var a = n(76),
        r = n.n(a),
        o = n(176),
        c = n(47),
        l = n(0),
        i = n.n(l),
        u = n(11),
        s = n(48),
        m = n(32),
        d = n(109),
        p = n.n(d),
        h = n(110),
        f = n(62),
        E = n(301),
        b = n(298),
        g = n.n(b),
        w = n(299),
        v = n.n(w),
        y = n(72),
        x = n.n(y),
        O = n(75),
        C = n.n(O),
        j = n(180),
        k = n.n(j),
        M = n(300),
        S = n.n(M),
        N = n(74),
        I = n.n(N),
        L = n(30),
        B = n.n(L),
        P = n(41),
        T = n.n(P),
        D = n(31),
        F = n.n(D),
        z = n(73),
        G = n.n(z),
        H = n(179),
        _ = n.n(H),
        J = n(111),
        A = n.n(J),
        R = n(282),
        U = n.n(R),
        V = n(77),
        q = n.n(V),
        K = n(283),
        W = n.n(K),
        Y = n(302),
        Q = n(178),
        X = n.n(Q),
        Z = n(293),
        $ = n.n(Z),
        ee = n(284),
        te = n.n(ee),
        ne = n(294),
        ae = n.n(ne),
        re = n(297),
        oe = n.n(re),
        ce = n(296),
        le = n.n(ce),
        ie = n(295),
        ue = n.n(ie),
        se = n(175),
        me = n.n(se),
        de = n(115),
        pe = n.n(de),
        he = n(285),
        fe = n.n(he),
        Ee = n(286),
        be = n.n(Ee),
        ge = n(287),
        we = n.n(ge),
        ve = n(288),
        ye = n(181);
      n(525);
      function xe(e, t, n) {
        void 0 === n && (n = 254);
        var a = 1 - e - t,
          r = (n / 254).toFixed(2),
          o = (r / t) * e,
          c = (r / t) * a,
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
      function Oe(e) {
        var t,
          n,
          a,
          r = 2e4 / e;
        return (
          r <= 66
            ? ((t = 255),
              (n = 99.4708025861 * Math.log(r) - 161.1195681661),
              (a =
                r <= 19
                  ? 0
                  : 138.5177312231 * Math.log(r - 10) - 305.0447927307))
            : ((t = 329.698727446 * Math.pow(r - 60, -0.1332047592)),
              (n = 288.1221695283 * Math.pow(r - 60, -0.0755148492)),
              (a = 255)),
          (t = t > 255 ? 255 : t),
          (n = n > 255 ? 255 : n),
          (a = a > 255 ? 255 : a),
          "#" +
            (
              16777216 +
              parseInt(a, 10) +
              256 * parseInt(n, 10) +
              65536 * parseInt(t, 10)
            )
              .toString(16)
              .substr(1)
        );
      }
      function Ce(e, t, n) {
        var a =
            0.664511 *
              (e =
                e > 0.04045 ? Math.pow((e + 0.055) / 1.055, 2.4) : e / 12.92) +
            0.154324 *
              (t =
                t > 0.04045 ? Math.pow((t + 0.055) / 1.055, 2.4) : t / 12.92) +
            0.162028 *
              (n =
                n > 0.04045 ? Math.pow((n + 0.055) / 1.055, 2.4) : n / 12.92),
          r = 0.283881 * e + 0.668433 * t + 0.047685 * n,
          o = 88e-6 * e + 0.07231 * t + 0.986039 * n,
          c = (a / (a + r + o)).toFixed(4),
          l = (r / (a + r + o)).toFixed(4);
        return (
          isNaN(c) && (c = 0),
          isNaN(l) && (l = 0),
          [parseFloat(c), parseFloat(l)]
        );
      }
      var je = {
        ct: function(e) {
          return Oe(e.state.ct);
        },
        xy: function(e) {
          var t = e.state,
            n = t.xy,
            a = void 0 === n ? [0, 0] : n,
            r = t.bri,
            o = void 0 === r ? 0 : r;
          return xe(a[0], a[1], o);
        }
      };
      function ke() {
        var e = Object(c.a)([
          "\n  margin-top: -0.5em !important;\n  margin-bottom: -0.5em !important;\n"
        ]);
        return (
          (ke = function() {
            return e;
          }),
          e
        );
      }
      function Me() {
        var e = Object(c.a)([
          "\n  width: 500px;\n  max-width: calc(100vw - 80px);\n"
        ]);
        return (
          (Me = function() {
            return e;
          }),
          e
        );
      }
      function Se() {
        var e = Object(c.a)([
          "\n  .rc-slider-rail {\n    background-image: linear-gradient(\n      to right,\n      #5373d8,\n      #c7e1fd,\n      #fae3a8,\n      #c14334\n    );\n  }\n  .rc-slider-track {\n    background: transparent;\n  }\n"
        ]);
        return (
          (Se = function() {
            return e;
          }),
          e
        );
      }
      var Ne = Object(s.b)(ye.a)(Se()),
        Ie = Object(s.b)(I.a)(Me()),
        Le = Object(s.b)(G.a)(ke()),
        Be = Object(m.a)(
          Object(m.d)("isDialogOpen", "setDialogOpen", !1),
          Object(m.d)("selectedLight", "setSelectedLight", void 0),
          Object(m.d)(
            "smallScreen",
            "setSmallScreen",
            window.matchMedia("(max-width: 800px)").matches
          ),
          Object(m.b)({
            componentDidMount: function() {
              var e = this;
              window.addEventListener(
                "resize",
                p()(500)(function() {
                  return e.props.setSmallScreen(
                    window.matchMedia("(max-width: 800px)").matches
                  );
                })
              );
            }
          })
        )(function(e) {
          var t = e.setColorTemperature,
            n = e.setColor,
            a = e.setBrightness,
            r = e.setState,
            o = e.room,
            c = e.lights,
            u = e.isDialogOpen,
            s = e.setDialogOpen,
            m = e.selectedLight,
            d = e.setSelectedLight,
            p = e.smallScreen;
          return i.a.createElement(
            I.a,
            {
              subheader: i.a.createElement(
                $.a,
                null,
                o.name,
                i.a.createElement(
                  X.a,
                  null,
                  i.a.createElement(C.a, {
                    checked: o.state.any_on,
                    onChange: function() {
                      return r(o, !o.state.any_on);
                    }
                  })
                )
              )
            },
            o.lights
              .filter(function(e) {
                return Boolean(c[e]);
              })
              .map(function(e) {
                return Object(h.a)({}, c[e], { id: e });
              })
              .map(function(e) {
                return i.a.createElement(
                  B.a,
                  { key: e.id },
                  i.a.createElement(
                    T.a,
                    null,
                    i.a.createElement(
                      Le,
                      {
                        onClick: function() {
                          s(!0), d(e);
                        }
                      },
                      e.state.on
                        ? i.a.createElement(A.a, {
                            color:
                              "ct" === e.state.colormode
                                ? Oe(e.state.ct)
                                : "xy" === e.state.colormode
                                ? xe(e.state.xy[0], e.state.xy[1], e.state.bri)
                                : "#fcf794"
                          })
                        : i.a.createElement(te.a, null)
                    )
                  ),
                  i.a.createElement(F.a, { primary: e.name }),
                  i.a.createElement(
                    X.a,
                    null,
                    i.a.createElement(C.a, {
                      checked: e.state.on,
                      onChange: function() {
                        return r(e, !e.state.on);
                      }
                    })
                  )
                );
              }),
            i.a.createElement(
              ae.a,
              {
                fullScreen: p,
                open: u,
                onClose: function() {
                  return s(!1);
                },
                "aria-labelledby": "alert-dialog-title",
                "aria-describedby": "alert-dialog-description"
              },
              m
                ? i.a.createElement(
                    l.Fragment,
                    null,
                    i.a.createElement(
                      ue.a,
                      { id: "alert-dialog-title" },
                      o.name,
                      " ",
                      m.name
                    ),
                    i.a.createElement(
                      le.a,
                      null,
                      i.a.createElement(
                        Ie,
                        null,
                        "bri" in m.state &&
                          i.a.createElement(
                            B.a,
                            null,
                            i.a.createElement(
                              pe.a,
                              null,
                              i.a.createElement(fe.a, { color: "white" })
                            ),
                            i.a.createElement(F.a, {
                              primary: i.a.createElement(ye.a, {
                                min: 0,
                                max: 255,
                                defaultValue: m.state.on ? m.state.bri : 0,
                                onChange: function(e) {
                                  return a(m, e);
                                }
                              }),
                              secondary: "Brightness"
                            })
                          ),
                        "ct" in m.state &&
                          i.a.createElement(
                            B.a,
                            null,
                            i.a.createElement(
                              pe.a,
                              null,
                              i.a.createElement(be.a, { color: "white" })
                            ),
                            i.a.createElement(F.a, {
                              primary: i.a.createElement(Ne, {
                                min: 153,
                                max: 500,
                                defaultValue: Math.max(
                                  153,
                                  Math.min(m.state.ct, 500)
                                ),
                                onChange: function(e) {
                                  return t(m, e);
                                }
                              }),
                              secondary: "Temperature"
                            })
                          ),
                        ("xy" in m.state || "hue" in m.state) &&
                          i.a.createElement(
                            B.a,
                            null,
                            i.a.createElement(
                              pe.a,
                              null,
                              i.a.createElement(we.a, { color: "white" })
                            ),
                            i.a.createElement(F.a, {
                              primary: i.a.createElement(ve.HuePicker, {
                                width: "100%",
                                color: xe(
                                  m.state.xy[0],
                                  m.state.xy[1],
                                  m.state.bri
                                ),
                                defaultColor: je[m.state.colormode](m),
                                onChange: function(e) {
                                  return n(m, e);
                                }
                              }),
                              secondary: "Color"
                            })
                          )
                      )
                    ),
                    i.a.createElement(
                      oe.a,
                      null,
                      i.a.createElement(
                        me.a,
                        {
                          onClick: function() {
                            return s(!1);
                          },
                          color: "primary",
                          autoFocus: !0
                        },
                        "Close"
                      )
                    )
                  )
                : i.a.createElement("span", null)
            )
          );
        });
      function Pe() {
        var e = Object(c.a)(["\n  flex: 1;\n"]);
        return (
          (Pe = function() {
            return e;
          }),
          e
        );
      }
      var Te = Object(s.a)(Pe()),
        De = function(e) {
          return Object.values(e).some(function(e) {
            return e.state.any_on;
          });
        },
        Fe = i.a.createElement(
          I.a,
          { component: "nav" },
          i.a.createElement(
            B.a,
            { button: !0, href: "/", component: "a" },
            i.a.createElement(T.a, null, i.a.createElement(A.a, null)),
            i.a.createElement(F.a, null, "Lights control")
          ),
          i.a.createElement(
            B.a,
            { button: !0, href: "/hue/linkbutton", component: "a" },
            i.a.createElement(T.a, null, i.a.createElement(U.a, null)),
            i.a.createElement(F.a, null, "Link device")
          ),
          i.a.createElement(
            B.a,
            { button: !0, href: "/hue", component: "a" },
            i.a.createElement(T.a, null, i.a.createElement(q.a, null)),
            i.a.createElement(F.a, null, "Import from bridge")
          ),
          i.a.createElement(
            B.a,
            { button: !0, href: "/tradfri", component: "a" },
            i.a.createElement(T.a, null, i.a.createElement(q.a, null)),
            i.a.createElement(F.a, null, "Import from Tradfri")
          ),
          i.a.createElement(
            B.a,
            { button: !0, href: "/deconz", component: "a" },
            i.a.createElement(T.a, null, i.a.createElement(q.a, null)),
            i.a.createElement(F.a, null, "Deconz")
          ),
          i.a.createElement(
            B.a,
            { button: !0, href: "/milight", component: "a" },
            i.a.createElement(T.a, null, i.a.createElement(q.a, null)),
            i.a.createElement(F.a, null, "Add MiLight Bulb")
          )
        ),
        ze = Object(E.withStyles)(function(e) {
          return {
            root: {
              flexGrow: 1,
              height: "100vh",
              zIndex: 1,
              overflow: "hidden",
              position: "relative",
              display: "flex"
            },
            appBar: Object(f.a)(
              { zIndex: e.zIndex.drawer + 1, marginLeft: 240 },
              e.breakpoints.up("md"),
              { width: "calc(100% - ".concat(240, "px)") }
            ),
            navIconHide: Object(f.a)({}, e.breakpoints.up("md"), {
              display: "none"
            }),
            toolbar: e.mixins.toolbar,
            drawerPaper: Object(f.a)({ width: 240 }, e.breakpoints.up("md"), {
              position: "relative"
            }),
            content: {
              flexGrow: 1,
              overflow: "auto",
              backgroundColor: e.palette.background.default,
              padding: 3 * e.spacing.unit,
              minWidth: 0
            }
          };
        })(function(e) {
          var t = e.classes,
            n = e.groups,
            a = e.lights,
            r = e.onColorTemperatureChange,
            o = e.onColorChange,
            c = e.onBrightnessChange,
            l = e.onStateChange,
            u = e.onGlobalStateChange;
          return i.a.createElement(Y.a, { initial: { drawer: !1 } }, function(
            e
          ) {
            var s = e.state,
              m = e.setState;
            return i.a.createElement(
              "div",
              { className: t.root },
              i.a.createElement(
                g.a,
                { position: "absolute", className: t.appBar },
                i.a.createElement(
                  v.a,
                  null,
                  i.a.createElement(
                    G.a,
                    {
                      onClick: function() {
                        return m({ drawer: !0 });
                      },
                      className: t.navIconHide
                    },
                    i.a.createElement(W.a, { color: "white" })
                  ),
                  i.a.createElement(
                    x.a,
                    { variant: "title", color: "inherit", className: Te },
                    "Hue Emulator"
                  ),
                  i.a.createElement(S.a, {
                    control: i.a.createElement(C.a, {
                      checked: De(n),
                      onChange: function() {
                        return u(!De(n));
                      }
                    }),
                    label: i.a.createElement(
                      "span",
                      { style: { color: "white" } },
                      "Turn all ",
                      De(n) ? "off" : "on"
                    )
                  })
                )
              ),
              i.a.createElement(
                _.a,
                { mdUp: !0 },
                i.a.createElement(
                  k.a,
                  {
                    variant: "temporary",
                    open: s.drawer,
                    onClose: function() {
                      return m({ drawer: !1 });
                    },
                    classes: { paper: t.drawerPaper },
                    ModalProps: { keepMounted: !0 }
                  },
                  i.a.createElement("div", { className: t.toolbar }),
                  Fe
                )
              ),
              i.a.createElement(
                _.a,
                { smDown: !0, implementation: "css" },
                i.a.createElement(
                  k.a,
                  {
                    variant: "permanent",
                    open: !0,
                    onClose: function() {
                      return m({ drawer: !1 });
                    },
                    classes: { paper: t.drawerPaper }
                  },
                  i.a.createElement("div", { className: t.toolbar }),
                  Fe
                )
              ),
              i.a.createElement(
                "main",
                { className: t.content },
                i.a.createElement("div", { className: t.toolbar }),
                Object.keys(n)
                  .map(function(e) {
                    return Object(h.a)({}, n[e], { id: e });
                  })
                  .map(function(e) {
                    return i.a.createElement(Be, {
                      key: e.id,
                      room: e,
                      lights: a,
                      setColorTemperature: r,
                      setColor: o,
                      setBrightness: c,
                      setState: l
                    });
                  })
              )
            );
          });
        });
      function Ge() {
        var e = Object(c.a)(["\n  html, body {\n    margin: 0;\n  }\n"]);
        return (
          (Ge = function() {
            return e;
          }),
          e
        );
      }
      function He(e, t) {
        return fetch(e, {
          method: "PUT",
          mode: "cors",
          body: JSON.stringify(t),
          headers: { "Content-Type": "application/json" }
        })
          .then(function(e) {
            return e;
          })
          .catch(function(e) {
            return console.error(e.message);
          });
      }
      n.d(t, "httpPutRequest", function() {
        return He;
      }),
        Object(s.c)(Ge());
      var _e = window.config.API_KEY,
        Je = p()(1e3),
        Ae = Object(m.a)(
          Object(m.d)("groups", "setGroups", {}),
          Object(m.d)("lights", "setLights", {}),
          Object(m.c)({
            onColorTemperatureChange: Je(function(e, t) {
              return He("/api/".concat(_e, "/lights/").concat(e.id, "/state"), {
                ct: t
              });
            }),
            onColorChange: Je(function(e, t) {
              return He("/api/".concat(_e, "/lights/").concat(e.id, "/state"), {
                xy: Ce(t.rgb.r, t.rgb.g, t.rgb.b)
              });
            }),
            onBrightnessChange: Je(function(e, t) {
              return He("/api/".concat(_e, "/lights/").concat(e.id, "/state"), {
                bri: t
              });
            }),
            onStateChange: function(e, t) {
              return He(
                "/api/"
                  .concat(_e, "/")
                  .concat(
                    "Room" === e.type
                      ? "groups/" + e.id + "/action"
                      : "lights/" + e.id + "/state"
                  ),
                { on: t }
              );
            },
            onGlobalStateChange: function(e) {
              return He("/api/".concat(_e, "/groups/0/action"), { on: e });
            }
          }),
          Object(m.b)({
            componentDidMount: (function() {
              var e = Object(o.a)(
                r.a.mark(function e() {
                  var t = this;
                  return r.a.wrap(
                    function(e) {
                      for (;;)
                        switch ((e.prev = e.next)) {
                          case 0:
                            setInterval(
                              Object(o.a)(
                                r.a.mark(function e() {
                                  var n, a;
                                  return r.a.wrap(
                                    function(e) {
                                      for (;;)
                                        switch ((e.prev = e.next)) {
                                          case 0:
                                            return (
                                              (e.next = 2),
                                              Promise.all([
                                                fetch(
                                                  "/api/".concat(_e, "/groups")
                                                ),
                                                fetch(
                                                  "/api/".concat(_e, "/lights")
                                                )
                                              ])
                                            );
                                          case 2:
                                            return (
                                              (n = e.sent),
                                              (e.next = 5),
                                              Promise.all([
                                                n[0].json(),
                                                n[1].json()
                                              ])
                                            );
                                          case 5:
                                            (a = e.sent),
                                              t.props.setGroups(a[0]),
                                              t.props.setLights(a[1]);
                                          case 8:
                                          case "end":
                                            return e.stop();
                                        }
                                    },
                                    e,
                                    this
                                  );
                                })
                              ),
                              1e3
                            );
                          case 1:
                          case "end":
                            return e.stop();
                        }
                    },
                    e,
                    this
                  );
                })
              );
              return function() {
                return e.apply(this, arguments);
              };
            })()
          })
        )(ze);
      Object(u.render)(
        i.a.createElement(Ae, null),
        document.getElementById("root")
      );
    }
  },
  [[304, 2, 1]]
]);
//# sourceMappingURL=main.b1024bd8.chunk.js.map
