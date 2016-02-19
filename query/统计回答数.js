db.getCollection("19551147_a").aggregate([
 {
   $group: {
     _id: "$qid",
     total: { $sum: 1 },
     answerer: {$push: "$answerer"},
     answer: {$push: "$$ROOT"}
   }
 },
 {
   $sort: {
     total: -1
   }
 }
]);
