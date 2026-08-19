/* Link analysis graph (vis-network) */

(function (global) {
    'use strict';

    var SIGNAL_COLORS = {
        keyword_match: '#f6c343',
        image_hash: '#f44336',
        reverse_image_match: '#e91e63',
        username_similarity: '#2196f3',
        name_overlap: '#4caf50',
        ocr_overlap: '#9c27b0'
    };

    var GROUP_COLORS = {
        keyword: {background: '#f6c343', border: '#c79a2e'},
        instagram: {background: '#e1306c', border: '#a02049'},
        facebook: {background: '#3b5998', border: '#27406f'},
        x: {background: '#111111', border: '#555555'},
        tiktok: {background: '#25f4ee', border: '#1aa8a3'},
        github: {background: '#6e5494', border: '#4c3a68'},
        linkedin: {background: '#0a66c2', border: '#084a8e'},
        gitlab: {background: '#fc6d26', border: '#c24d13'},
        unknown: {background: '#607d8b', border: '#43545e'}
    };

    var VIS = global.vis;

    function App() {
        this.report = null;
        this.network = null;
        this.nodes = null;
        this.edges = null;
        this.filteredSignals = {};
    }

    App.prototype.init = function () {
        var self = this;

        OSINT.api('/api/sessions').then(function (data) {
            var options = (data.sessions || []).map(function (s) {
                return '<option value="' + OSINT.esc(s.scan_id) + '">' +
                    OSINT.esc(s.scan_id + ' - ' + (s.target || '-')) + '</option>';
            });
            $('#sessionSelect').html(
                '<option value="">Select session...</option>' + options.join('')
            );
        });

        var session = OSINT.qs('session');
        if (session) {
            setTimeout(function () {
                $('#sessionSelect').val(session);
                self.load(session);
            }, 300);
        }

        $('#sessionSelect').on('change', function () {
            var v = $(this).val();
            if (v) self.load(v);
        });
    };

    App.prototype.load = function (scanId) {
        var self = this;
        OSINT.api('/api/reports/' + encodeURIComponent(scanId) + '/graph')
            .then(function (graph) {
                self.nodes = graph.nodes;
                self.edges = graph.edges;
                self.report = graph;

                self.filteredSignals = {};
                var signals = {};
                graph.edges.forEach(function (edge) {
                    signals[edge.signal] = true;
                });
                var filters = Object.keys(signals).map(function (signal) {
                    return '<label style="cursor:pointer;">' +
                        '<input type="checkbox" class="signalFilter" data-signal="' +
                        OSINT.esc(signal) + '" checked> ' +
                        '<i style="background:' + self.color(signal) + '"></i>' +
                        OSINT.esc(signal) + '</label>';
                });
                $('#signalFilters').html(filters.join(''));

                $('.signalFilter').on('change', function () {
                    var signal = $(this).data('signal');
                    if ($(this).is(':checked')) {
                        delete self.filteredSignals[signal];
                    } else {
                        self.filteredSignals[signal] = true;
                    }
                    self.render();
                });

                self.renderLegend(signals);
                self.render();
            });
    };

    App.prototype.color = function (signal) {
        return SIGNAL_COLORS[signal] || '#9e9e9e';
    };

    App.prototype.renderLegend = function (signals) {
        var html = Object.keys(signals).map(function (signal) {
            return '<span><i style="background:' + this.color(signal) + '"></i>' +
                OSINT.esc(signal) + '</span>';
        }.bind(this)).join('');
        $('#legend').html(html);
    };

    App.prototype.visibleEdges = function () {
        var self = this;
        return this.edges.filter(function (edge) {
            return !self.filteredSignals[edge.signal];
        });
    };

    App.prototype.render = function () {
        var self = this;
        var visible = this.visibleEdges();

        var visibleIds = {};
        visible.forEach(function (edge) {
            visibleIds[edge.from] = true;
            visibleIds[edge.to] = true;
        });

        var nodes = new VIS.DataSet(
            this.nodes.filter(function (node) {
                return visibleIds[node.id];
            }).map(function (node) {
                var group = GROUP_COLORS[node.group] || GROUP_COLORS.unknown;
                var color = group.background;
                var size = 10 + Math.min(30, (node.risk_score || 0) * 2);
                return {
                    id: node.id,
                    label: OSINT.shorten(node.label || node.id, 22),
                    title: node.id,
                    group: node.group,
                    shape: node.shape || 'dot',
                    size: node.shape === 'star' ? 18 : size,
                    color: node.color || color,
                    meta: node
                };
            })
        );

        var edges = new VIS.DataSet(visible.map(function (edge) {
            return {
                from: edge.from,
                to: edge.to,
                label: '',
                title: edge.signal + ' (' + edge.value + ') ' + edge.evidence,
                color: {color: this.color(edge.signal), highlight: '#ffffff'},
                width: 1 + Math.min(4, edge.value * 4),
                signal: edge.signal
            };
        }.bind(this)));

        var container = document.getElementById('graphContainer');
        var data = {nodes: nodes, edges: edges};
        var options = {
            physics: {
                stabilization: {enabled: true, iterations: 200},
                barnesHut: {gravitationalConstant: -8000, springLength: 120}
            },
            interaction: {hover: true, tooltipDelay: 100},
            nodes: {font: {color: '#ffffff', size: 13}}
        };

        if (this.network) {
            this.network.setData(data);
            return;
        }

        this.network = new VIS.Network(container, data, options);
        this.network.on('click', function (params) {
            self.showDetails(params);
        });
    };

    App.prototype.showDetails = function (params) {
        if (!params.nodes || !params.nodes.length) return;
        var nodeId = params.nodes[0];
        var node = this.nodes.find(function (n) { return n.id === nodeId; });

        var connected = this.visibleEdges().filter(function (edge) {
            return edge.from === nodeId || edge.to === nodeId;
        });

        var html = '<h5 class="text-white">' + OSINT.esc(nodeId) + '</h5>';
        if (node && node.group === 'keyword') {
            html += '<p class="text-white">Target keyword node</p>';
        } else if (node) {
            html += '<p class="text-white">Platform: <b>' + OSINT.esc(node.group) + '</b></p>';
            html += '<p class="text-white">Risk: ' + OSINT.riskBadge(
                OSINT.riskLevel(node.risk_score || 0), node.risk_score || 0
            ) + '</p>';
            html += '<p class="text-white">Keyword match: <b>' + (node.matched ? 'yes' : 'no') + '</b></p>';
        }
        html += '<p class="text-white mt-2">Connections: <b>' + connected.length + '</b></p>';
        if (connected.length) {
            html += '<ul class="text-white small">';
            connected.slice(0, 12).forEach(function (edge) {
                html += '<li><i style="display:inline-block;width:10px;height:10px;background:' +
                    this.color(edge.signal) + '"></i> ' + OSINT.esc(edge.signal) +
                    ' &rarr; ' + OSINT.esc(OSINT.shorten(
                        edge.from === nodeId ? edge.to : edge.from, 44
                    )) + '</li>';
            }.bind(this));
            html += '</ul>';
        }
        $('#nodeDetails').html(html);
    };

    $(function () {
        new App().init();
    });
})(window);
