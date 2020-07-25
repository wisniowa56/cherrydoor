db = db.getSiblingDB("admin");
load("install/config.js");
db = db.getSiblingDB(config.mongo.name);
try {
  db.createUser({
    user: config.mongo.username,
    pwd: config.mongo.password,
    roles: [
      { role: "readWrite", db: config.mongo.name },
      { role: "clusterMonitor", db: "admin" },
    ],
  });
} catch (e) {}
db.createCollection("users");
db.createCollection("logs");
db.createCollection("settings");

if (user != {} && user.username != "" && user.password != "") {
  db.users.insert({
    username: user.username,
    password: user.password,
    cards: [],
  });
}
