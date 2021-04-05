/**
 * "Yet Another Multicolumn Layout" - YAML CSS Framework
 *
 * (en) Workaround for IE8 und Webkit browsers to fix focus problems when using skiplinks
 * (de) Workaround für IE8 und Webkit browser, um den Focus zu korrigieren, bei Verwendung von Skiplinks
 *
 * @note			inspired by Paul Ratcliffe's article
 *					http://www.communis.co.uk/blog/2009-06-02-skip-links-chrome-safari-and-added-wai-aria
 *                  Many thanks to Mathias Schäfer (http://molily.de/) for his code improvements
 *
 * @copyright       © 2005-2013, Dirk Jesse
 * @license         CC-BY 2.0 (http://creativecommons.org/licenses/by/2.0/),
 *                  YAML-CDL (http://www.yaml.de/license.html)
 * @link            http://www.yaml.de
 * @package         yaml
 * @version         4.0+
 */

(function () {
	let YAML_focusFix = {
		skipClass : 'ym-skip',

		init : function () {
			let userAgent = navigator.userAgent.toLowerCase();
			let	is_webkit = userAgent.indexOf('webkit') > -1;
			let	is_ie = userAgent.indexOf('msie') > -1;

			if (is_webkit || is_ie) {
				let body = document.body,
					handler = YAML_focusFix.click;
				if (body.addEventListener) {
					body.addEventListener('click', handler, false);
				} else if (body.attachEvent) {
					body.attachEvent('onclick', handler);
				}
			}
		},

		trim : function (str) {
			return str.replace(/^\s\s*/, '').replace(/\s\s*$/, '');
		},

		click : function (e) {
			e = e || window.event;
			let target = e.target || e.srcElement;
			let a = target.className.split(' ');

			for (let i=0; i < a.length; i++) {
				let cls = YAML_focusFix.trim(a[i]);
				if ( cls === YAML_focusFix.skipClass) {
					YAML_focusFix.focus(target);
					break;
				}
			}
		},

		focus : function (link) {
			if (link.href) {
				let href = link.href,
					id = href.substr(href.indexOf('#') + 1),
					target = document.getElementById(id);
				if (target) {
					target.setAttribute("tabindex", "-1");
					target.focus();
				}
			}
		}
	};
	YAML_focusFix.init();
})();
