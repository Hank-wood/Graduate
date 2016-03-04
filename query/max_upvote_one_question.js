db = db.getSiblingDB("sg1");

db.getCollection("19551147_a").aggregate(
    [
        {
            $match: {"qid": "40617404"}
        },
        {
            $project: {
                url: 1,
                upvoters: 1,
                aid: 1,
                upvote_count: {$size: "$upvoters"}
            }
        },
        {
            $sort: {upvote_count: -1}
        }
    ]
);
