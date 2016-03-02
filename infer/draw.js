var radius = 960 / 2;

var cluster = d3.layout.cluster()
    .size([360, radius - 120]);

var diagonal = d3.svg.diagonal.radial()
    .projection(function(d) { return [d.y, d.x / 180 * Math.PI]; });

var svg = d3.select("body").append("svg")
    .attr("width", radius * 2)
    .attr("height", radius * 2)
  .append("g")
    .attr("transform", "translate(" + radius + "," + radius + ")");

d3.json("data/dump.json", function(error, root) {
    var edgeNames = {};
    root["links"].forEach(function(link){
        edgeNames[link["source"] + ':' + link["target"]] = link["reltype"];
    });
  if (error) throw error;

  var nodes = cluster.nodes(root);



  var linkg = svg.selectAll(".link")
    .data(cluster.links(nodes))
    .enter().append("g")
    .attr("class", "link");

linkg.append("path")
    .attr("class", "link")
    .attr("d", diagonal);

linkg.append("text")
    //.attr("x", function(d) {
    //  return (d.source.y + d.target.y) / 2;
    //})
    //.attr("y", function(d) {
    //  return (d.source.x + d.target.x) / 2;
        //return d.target.x / 180 * Math.PI
    //})
    .attr("text-anchor", "middle")
    .text(function(d) {
        return edgeNames[d.source['id'] + ':' + d.target['id']];
    })
    .attr("transform", function(d) {
        return "rotate(" + (d.target.x - 90) + ")translate(" + d.target.y*5/6 + ")"; })

    /*
  var link = svg.selectAll("path.link")
      .data(cluster.links(nodes))
    .enter().append("path")
      .attr("class", "link")
      .attr("d", diagonal);
      */

  var node = svg.selectAll("g.node")
      .data(nodes)
    .enter().append("g")
      .attr("class", "node")
      .attr("transform", function(d) {
          return "rotate(" + (d.x - 90) + ")translate(" + d.y + ")"; });

  node.append("circle")
      .attr("r", 4.5);

  node.append("text")
      .attr("dy", ".31em")
      .attr("text-anchor", function(d) {
          return d.x < 180 ? "start" : "end"; })
      .attr("transform", function(d) { return d.x < 180 ? "translate(8)" : "rotate(180)translate(-8)"; })
      .text(function(d) { return d.id; });
});

d3.select(self.frameElement).style("height", radius * 2 + "px");
