// src/backgroundAnimation.js

let t = 0;

function mag(x, y) {
    return Math.sqrt(x * x + y * y);
}

function a(x, y, d = mag(k = x/8-12, e = y/8-9)**2/50) {
    stroke(99 + 99/Math.abs(k) * Math.sin(t*4 + e*e)**2, 96);
    let q = x/3 + e + 60 + 1/k + k/Math.sin(e)*Math.sin(d-t);
    let c = d/4 - t/8;
    point(q * Math.sin(c) + 200, (q - y*d/9) * Math.cos(c) + 200);
}

function setup() {
    // 创建背景画布
    let canvas = createCanvas(window.innerWidth, window.innerHeight);
    canvas.parent('background');

    // 设置画布透明度
    clear(); // 清除画布内容，保持透明
}

function draw() {
    // 清除画布内容，保持透明
    clear();

    t += PI/90;
    for (let i = 0; i < 10000; i++) {
        a(i % 200, (i/200) << 2);
    }
}