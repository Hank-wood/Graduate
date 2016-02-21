db = db.getSiblingDB("zhihu_data");

db.getCollection("19551147_a").aggregate(
    [
        {
            $group: {
                _id: "$qid",
                total: { $sum: 1 },
                answerer: {
                    $push: {
                        "id": "$answerer",
                        "time": "$time"
                    }
                }
                //answer: {$push: "$$ROOT"}
            }
        },
        {
            $sort: {
                total: -1
            }
        },
        {
            $limit: 5
        }
    ]
).forEach(function(d){
    printjson(d);
});
