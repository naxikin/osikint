/* Social OSINT dashboard helpers */

(function (global) {
    'use strict';

    var OSINT = {};

    OSINT.api = function (url, options) {
        options = options || {};
        options.headers = options.headers || {};
        if (options.body) {
            options.headers['Content-Type'] = 'application/json';
        }
        return fetch(url, options).then(function (res) {
            return res.json().then(function (data) {
                if (!res.ok) {
                    var err = new Error(data.error || ('HTTP ' + res.status));
                    err.status = res.status;
                    if (res.status === 401) {
                        window.location.href = '/login?next=' +
                            encodeURIComponent(window.location.pathname + window.location.search);
                    }
                    throw err;
                }
                return data;
            });
        });
    };

    OSINT.qs = function (name) {
        var params = new URLSearchParams(window.location.search);
        return params.get(name) || '';
    };

    OSINT.esc = function (value) {
        if (value === null || value === undefined) return '';
        return String(value)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;');
    };

    OSINT.shorten = function (value, max) {
        value = String(value || '');
        return value.length > max ? value.slice(0, max - 3) + '...' : value;
    };

    OSINT.fmt = function (iso) {
        if (!iso) return '-';
        var d = new Date(iso);
        return isNaN(d) ? iso : d.toLocaleString();
    };

    OSINT.stateBadge = function (state) {
        state = state || 'unknown';
        var cls = 'badge-queued';
        if (state === 'completed') cls = 'badge-completed';
        else if (state === 'failed') cls = 'badge-failed';
        else if (state === 'stopped') cls = 'badge-stopped';
        else if (state === 'running') cls = 'badge-running';
        return '<span class="ddx-badge ' + cls + '">' + OSINT.esc(state) + '</span>';
    };

    OSINT.riskBadge = function (level, score) {
        return '<span class="ddx-badge badge-' + OSINT.esc(level) + '">' +
            score + ' ' + OSINT.esc(level) + '</span>';
    };

    OSINT.riskLevel = function (score) {
        if (score <= 0) return 'none';
        if (score <= 5) return 'low';
        if (score <= 10) return 'medium';
        return 'high';
    };

    global.OSINT = OSINT;
})(window);
