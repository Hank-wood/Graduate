db = db.getSiblingDB("zhihu_data");
collections = db.getCollectionNames();

collections.forEach(function(colName){
    if (colName.indexOf('system') == -1 && colName.indexOf('user') == -1) {
        print("drop collection" + colName);
        db.getCollection(colName).drop();
    }
});
