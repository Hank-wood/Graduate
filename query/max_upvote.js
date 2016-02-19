db.getCollection("19551147_a").aggregate([
  {
    $project: {
      url: 1,
      upvoters: 1,
      upvote_count: {$size: "$upvoters"}
    }
  },
  {
    $sort: {upvote_count: -1}
  }
]);
