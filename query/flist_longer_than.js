db = db.getSiblingDB("zhihu_data");

db.user.find({
    $and: [
        {followee: {$exists: true}},
        {'$where': 'this.followee.length > 1'}
    ]
});
