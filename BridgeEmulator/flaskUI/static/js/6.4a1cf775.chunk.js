(this.webpackJsonpdiyhue=this.webpackJsonpdiyhue||[]).push([[6],{81:function(e,t,n){"use strict";n.d(t,"a",(function(){return s}));n(1);var r=n(10),o=n(82),i=n.n(o),u=n(5);function s(e){e.type;var t=e.message,n=e.duration,o=e.setType;return Object(u.jsx)(i.a,{duration:n,persistOnHover:!0,children:Object(u.jsx)("div",{className:"notificationContainer",children:Object(u.jsxs)("div",{className:"notification success",children:[Object(u.jsx)("p",{children:t}),Object(u.jsx)("div",{className:"icon",children:Object(u.jsx)(r.n,{onClick:function(){return o("none")}})})]})})})}},82:function(e,t,n){e.exports=function(){var e={433:function(e,t,n){"use strict";var r=n(642);function o(){}function i(){}i.resetWarningCache=o,e.exports=function(){function e(e,t,n,o,i,u){if(u!==r){var s=new Error("Calling PropTypes validators directly is not supported by the `prop-types` package. Use PropTypes.checkPropTypes() to call them. Read more at http://fb.me/use-check-prop-types");throw s.name="Invariant Violation",s}}function t(){return e}e.isRequired=e;var n={array:e,bool:e,func:e,number:e,object:e,string:e,symbol:e,any:e,arrayOf:t,element:e,elementType:e,instanceOf:t,node:e,objectOf:t,oneOf:t,oneOfType:t,shape:t,exact:t,checkPropTypes:i,resetWarningCache:o};return n.PropTypes=n,n}},74:function(e,t,n){e.exports=n(433)()},642:function(e){"use strict";e.exports="SECRET_DO_NOT_PASS_THIS_OR_YOU_WILL_BE_FIRED"},368:function(e,t,r){"use strict";r.r(t),r.d(t,{default:function(){return y}});var o=n(1),i=r.n(o),u=r(74);function s(e){return(s="function"==typeof Symbol&&"symbol"==typeof Symbol.iterator?function(e){return typeof e}:function(e){return e&&"function"==typeof Symbol&&e.constructor===Symbol&&e!==Symbol.prototype?"symbol":typeof e})(e)}function c(e,t){return(c=Object.setPrototypeOf||function(e,t){return e.__proto__=t,e})(e,t)}function a(e,t){return!t||"object"!==s(t)&&"function"!=typeof t?f(e):t}function f(e){if(void 0===e)throw new ReferenceError("this hasn't been initialised - super() hasn't been called");return e}function p(e){return(p=Object.setPrototypeOf?Object.getPrototypeOf:function(e){return e.__proto__||Object.getPrototypeOf(e)})(e)}var l=function(e){!function(e,t){if("function"!=typeof t&&null!==t)throw new TypeError("Super expression must either be null or a function");e.prototype=Object.create(t&&t.prototype,{constructor:{value:e,writable:!0,configurable:!0}}),t&&c(e,t)}(u,e);var t,n,r,o=(n=u,r=function(){if("undefined"==typeof Reflect||!Reflect.construct)return!1;if(Reflect.construct.sham)return!1;if("function"==typeof Proxy)return!0;try{return Date.prototype.toString.call(Reflect.construct(Date,[],(function(){}))),!0}catch(e){return!1}}(),function(){var e,t=p(n);if(r){var o=p(this).constructor;e=Reflect.construct(t,arguments,o)}else e=t.apply(this,arguments);return a(this,e)});function u(e){var t;return function(e,t){if(!(e instanceof t))throw new TypeError("Cannot call a class as a function")}(this,u),(t=o.call(this,e)).state={isVisible:!0},t.hide=t.hide.bind(f(t)),t.resumeTimer=t.resumeTimer.bind(f(t)),t.pauseTimer=t.pauseTimer.bind(f(t)),t}return(t=[{key:"componentDidMount",value:function(){var e=this.props.duration;this.remaining=e,this.resumeTimer()}},{key:"componentWillUnmount",value:function(){clearTimeout(this.timer)}},{key:"hide",value:function(){this.setState({isVisible:!1})}},{key:"resumeTimer",value:function(){window.clearTimeout(this.timer),this.start=new Date,this.timer=setTimeout(this.hide,this.remaining)}},{key:"pauseTimer",value:function(){this.props.persistOnHover&&(clearTimeout(this.timer),this.remaining-=new Date-this.start)}},{key:"render",value:function(){var e=this.state.isVisible,t=this.props.children;return e?i().createElement("div",{onMouseEnter:this.pauseTimer,onMouseLeave:this.resumeTimer},t):null}}])&&function(e,t){for(var n=0;n<t.length;n++){var r=t[n];r.enumerable=r.enumerable||!1,r.configurable=!0,"value"in r&&(r.writable=!0),Object.defineProperty(e,r.key,r)}}(u.prototype,t),u}(o.Component);l.defaultProps={duration:5e3,children:null,persistOnHover:!0},l.propTypes={children:u.node,duration:u.number,persistOnHover:u.bool};var y=l}},t={};function r(n){if(t[n])return t[n].exports;var o=t[n]={exports:{}};return e[n](o,o.exports,r),o.exports}return r.n=function(e){var t=e&&e.__esModule?function(){return e.default}:function(){return e};return r.d(t,{a:t}),t},r.d=function(e,t){for(var n in t)r.o(t,n)&&!r.o(e,n)&&Object.defineProperty(e,n,{enumerable:!0,get:t[n]})},r.o=function(e,t){return Object.prototype.hasOwnProperty.call(e,t)},r.r=function(e){"undefined"!=typeof Symbol&&Symbol.toStringTag&&Object.defineProperty(e,Symbol.toStringTag,{value:"Module"}),Object.defineProperty(e,"__esModule",{value:!0})},r(368)}()},89:function(e,t,n){"use strict";n.r(t);var r=n(13),o=n(1),i=(n(15),n(81)),u=n(5);t.default=function(e){e.API_KEY;var t=Object(o.useState)("none"),n=Object(r.a)(t,2),s=n[0],c=n[1],a=Object(o.useState)("no message"),f=Object(r.a)(a,2),p=f[0];f[1];return Object(u.jsxs)("div",{className:"content",children:["none"!==s&&Object(u.jsx)(i.a,{type:s,message:p,duration:"5000",setType:c}),Object(u.jsx)("p",{children:" Work in progress"})]})}}}]);
//# sourceMappingURL=6.4a1cf775.chunk.js.map