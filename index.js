var Blynk = require('blynk-library');
var config = require('./config');

var AUTH = config.AUTH;

var blynk = new Blynk.Blynk(AUTH);

var v0 = new blynk.VirtualPin(0);//askbid
var v1 = new blynk.VirtualPin(1);//price
var v2 = new blynk.VirtualPin(2);//upper
var v3 = new blynk.VirtualPin(3);//lower
var v4 = new blynk.VirtualPin(4);//macd
var v5 = new blynk.VirtualPin(5);//xem
var v6 = new blynk.VirtualPin(6);//yen
var v7 = new blynk.VirtualPin(7);//bid-price
var v8 = new blynk.VirtualPin(8);//ask-price
var v9 = new blynk.VirtualPin(9);//history
var v10 = new blynk.VirtualPin(10);//history
var v11 = new blynk.VirtualPin(11);//mean_price
var v12 = new blynk.VirtualPin(12);//trade-size
var v13 = new blynk.VirtualPin(13);//threshold-buy
var v14 = new blynk.VirtualPin(14);//threshold-sell
var v15 = new blynk.VirtualPin(15);//基準価格リセット
var v16 = new blynk.VirtualPin(16);//基準価格

v1.on('read', function() {
  const fs = require('fs');
  const price = fs.readFileSync("/var/tmp/last_price.txt", {encoding: "utf-8"});
  v1.write(price);
});

v2.on('read', function() {
  const fs = require('fs');
  const upper = fs.readFileSync("/var/tmp/upper.txt", {encoding: "utf-8"});
  v2.write(upper);
});

v3.on('read', function() {
  const fs = require('fs');
  const lower = fs.readFileSync("/var/tmp/lower.txt", {encoding: "utf-8"});
  v3.write(lower);
});

v4.on('read', function() {
  const fs = require('fs');
  const macd = fs.readFileSync("/var/tmp/MACD.txt", {encoding: "utf-8"});
  v4.write(macd);
});

v5.on('read', function() {
  const fs = require('fs');
  const xem = fs.readFileSync("/var/tmp/my-xem.txt", {encoding: "utf-8"});
  v5.write(xem);
});

v6.on('read', function() {
  const fs = require('fs');
  const yen = fs.readFileSync("/var/tmp/my-fund.txt", {encoding: "utf-8"});
  v6.write(yen);
});

v7.on('read', function() {
  const fs = require('fs');
  const bidprice = fs.readFileSync("/var/tmp/ask-price.txt", {encoding: "utf-8"});
  v7.write(bidprice);
});

v8.on('read', function() {
  const fs = require('fs');
  const askprice = fs.readFileSync("/var/tmp/bid-price.txt", {encoding: "utf-8"});
  v8.write(askprice);
});

v11.on('read', function() {
  const fs = require('fs');
  const meanprice = fs.readFileSync("/var/tmp/mean.txt", {encoding: "utf-8"});
  v11.write(meanprice);
});

v0.on('read', function() {
  const fs = require('fs');
  const askbid = fs.readFileSync("/var/tmp/ask-bid.txt", {encoding: "utf-8"});
  const history = fs.readFileSync("/var/tmp/history.txt", {encoding: "utf-8"});
  const timestamp = fs.readFileSync("/var/tmp/timestamp.txt", {encoding: "utf-8"});
  var trade_size = parseFloat(fs.readFileSync("/home/pi/zaif/trade-size.txt"));
  var threshold_buy = parseFloat(fs.readFileSync("/var/tmp/threshold-buy.txt"));
  var threshold_sell = parseFloat(fs.readFileSync("/var/tmp/threshold-sell.txt"));
  var mylastprice = parseFloat(fs.readFileSync("/var/tmp/mylastprice.txt"));
  v0.write(askbid);
  v9.write(timestamp);
  v10.write(history);
  v12.write(String(trade_size));
  v13.write(String(threshold_buy * 10000));
  v14.write(String(threshold_sell * 10000));
  v16.write(String(mylastprice));
});

v12.on('write', function(param) {
  const fs = require('fs');
  fs.writeFileSync("/home/pi/zaif/trade-size.txt", param[0]);
});

//v13.on('write', function(param) {
//  const fs = require('fs');
//  fs.writeFileSync("/var/tmp/threshold-buy.txt", param[0]/10000);
//});

//v14.on('write', function(param) {
//  const fs = require('fs');
//  fs.writeFileSync("/var/tmp/threshold-sell.txt", param[0]/10000);
//});

v15.on('write', function(param) {
  const fs = require('fs');
  var last_price = parseFloat(fs.readFileSync("/var/tmp/last_price.txt"));
  fs.writeFileSync("/var/tmp/mylastprice.txt", last_price);
});



