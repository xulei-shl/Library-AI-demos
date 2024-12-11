document.addEventListener('DOMContentLoaded', function() {
    const modelContainer = document.getElementById('modelContainer');
});

function setupCodeScroll() {
    const codeScroll = document.getElementById('codeScroll');
    if (codeScroll) {
        const content = codeScroll.innerHTML;
        codeScroll.innerHTML = content + content;
        codeScroll.addEventListener('animationend', () => {
            codeScroll.style.transform = 'translateY(0)';
            void codeScroll.offsetWidth;
            codeScroll.style.animation = 'none';
            setTimeout(() => {
                codeScroll.style.animation = 'scrollText 20s linear infinite';
            }, 10);
        });
    }
}

document.addEventListener('DOMContentLoaded', setupCodeScroll);

document.addEventListener('DOMContentLoaded', function() {
    const codeScrollElement = document.getElementById('codeScroll');
    fetch('src/demo.js')
        .then(response => response.text())
        .then(data => {
            codeScrollElement.textContent = data;
        })
        .catch(error => {
            console.error('Error reading demo.js:', error);
            codeScrollElement.textContent = 'Error loading code.';
        });
});

// src/particleText.js

const COLOR = "#65B4C9"; // 设定粒子特效颜色
let MESSAGE = "一个古代青铜酒器"; // 根据标签的ID获取待处理的文字内容

let FONT_SIZE = (window.innerWidth * 0.08); // 字体大小
let AMOUNT = 6000; // 设定粒子数量
let SIZE = 2; // 粒子大小
let INITIAL_DISPLACEMENT = 500; // 最初位移量
const INITIAL_VELOCITY = 7.5; // 最初速度
const VELOCITY_RETENTION = 0.95; // 速度保持
let SETTLE_SPEED = 0.7; // 稳定速度
const FLEE_SPEED = 0.5; // 逃逸速度
const FLEE_DISTANCE = 50; // 逃逸距离
let FLEE = true; // 逃逸模式
let SCATTER_VELOCITY = 3; // 散射速度
const SCATTER = true; // 散射模式

// 若处于移动设备展示
if (/Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent)) {
    // Mobile
    MESSAGE = "一个古代青铜酒器"; // 通过标签ID获取文本内容

    FONT_SIZE = 50;  // 字体大小减小
    AMOUNT = 300; // 粒子数量减少
    SIZE = 2;
    INITIAL_DISPLACEMENT = 100; // 最初位移量减少
    SETTLE_SPEED = 1; // 最初速度减少
    FLEE = false; // 关闭逃逸模式
    SCATTER_VELOCITY = 2; // 散射速度
}

const canvas = document.createElement("canvas");
canvas.id = "particleTextCanvas";
document.getElementById("modelContainer").appendChild(canvas);
const ctx = canvas.getContext("2d"); // 创建画布

let POINTS = [];
const MOUSE = {
    x: 0,
    y: 0
};

function Point(x, y, r, g, b, a) {
    const angle = Math.random() * 6.28;
    this.x = canvas.width / 2 - x + (Math.random() - 0.5) * INITIAL_DISPLACEMENT;
    this.y = canvas.height / 2 - y + (Math.random() - 0.5) * INITIAL_DISPLACEMENT;
    this.velx = INITIAL_VELOCITY * Math.cos(angle);
    this.vely = INITIAL_VELOCITY * Math.sin(angle);
    this.target_x = canvas.width / 2 - x;
    this.target_y = canvas.height / 2 - y;
    this.r = r;
    this.g = g;
    this.b = b;
    this.a = a;

    this.getX = function () {
        return this.x;
    }

    this.getY = function () {
        return this.y;
    }
    this.fleeFrom = function () {
        this.velx -= ((MOUSE.x - this.x) * FLEE_SPEED / 10);
        this.vely -= ((MOUSE.y - this.y) * FLEE_SPEED / 10);
    }

    this.settleTo = function () {
        this.velx += ((this.target_x - this.x) * SETTLE_SPEED / 100);
        this.vely += ((this.target_y - this.y) * SETTLE_SPEED / 100);
        this.velx -= this.velx * (1 - VELOCITY_RETENTION);
        this.vely -= this.vely * (1 - VELOCITY_RETENTION);
    }

    this.scatter = function () {
        const unit = this.unitVecToMouse();
        const vel = SCATTER_VELOCITY * 10 * (0.5 + Math.random() / 2);
        this.velx = -unit.x * vel;
        this.vely = -unit.y * vel;
    }

    this.move = function () {
        if (this.distanceToMouse() <= FLEE_DISTANCE) {
            this.fleeFrom();
        } else {
            this.settleTo();
        }

        if (this.x + this.velx < 0 || this.x + this.velx >= canvas.width) {
            this.velx *= -1;
        }
        if (this.y + this.vely < 0 || this.y + this.vely >= canvas.height) {
            this.vely *= -1;
        }

        this.x += this.velx;
        this.y += this.vely;
    }
    this.distanceToMouse = function () {
        return this.distanceTo(MOUSE.x, MOUSE.y);
    }

    this.distanceTo = function (x, y) {
        return Math.sqrt((x - this.x) * (x - this.x) + (y - this.y) * (y - this.y));
    }
    this.unitVecToMouse = function () {
        return this.unitVecTo(MOUSE.x, MOUSE.y);
    }

    this.unitVecTo = function (x, y) {
        const dx = x - this.x;
        const dy = y - this.y;
        return {
            x: dx / Math.sqrt(dx * dx + dy * dy),
            y: dy / Math.sqrt(dx * dx + dy * dy)
        };
    }
}

window.addEventListener("resize", function () {
    resizeCanvas()
    adjustText()
});

if (FLEE) {
    window.addEventListener("mousemove", function (event) {
        MOUSE.x = event.clientX;
        MOUSE.y = event.clientY;
    });
}

if (SCATTER) {
    window.addEventListener("click", function (event) {
        MOUSE.x = event.clientX;
        MOUSE.y = event.clientY;
        for (let i = 0; i < POINTS.length; i++) {
            POINTS[i].scatter();
        }
    });
}

function resizeCanvas() {
    canvas.width = document.getElementById("modelContainer").offsetWidth;
    canvas.height = document.getElementById("modelContainer").offsetHeight;
}

function adjustText() {
    ctx.fillStyle = COLOR;
    ctx.textBaseline = "middle";
    ctx.textAlign = "center";
    ctx.font = `${FONT_SIZE}px 仓耳玉楷`;
    ctx.fillText(MESSAGE, canvas.width / 2, canvas.height / 2);
    const textWidth = ctx.measureText(MESSAGE).width;
    if (textWidth === 0) {
        return;
    }
    const minX = canvas.width / 2 - textWidth / 2;
    const minY = canvas.height / 2 - FONT_SIZE / 2;
    const data = ctx.getImageData(minX, minY, textWidth, FONT_SIZE).data;
    let isBlank = true;
    for (let i = 0; i < data.length; i++) {
        if (data[i] !== 0) {
            isBlank = false;
            break;
        }
    }

    if (!isBlank) {
        let count = 0;
        let curr = 0;
        let num = 0;
        let x = 0;
        let y = 0;
        const w = Math.floor(textWidth);
        POINTS = [];
        while (count < AMOUNT) {
            while (curr === 0) {
                num = Math.floor(Math.random() * data.length);
                curr = data[num];
            }
            num = Math.floor(num / 4);
            x = w / 2 - num % w;
            y = FONT_SIZE / 2 - Math.floor(num / w);
            POINTS.push(new Point(x, y, data[num * 4], data[num * 4 + 1], data[num * 4 + 2], data[num * 4 + 3]));
            curr = 0;
            count++;
        }
    }
}

function init() {
    resizeCanvas()
    adjustText()
    window.requestAnimationFrame(animate);
}

function animate() {
    update();
    draw();
}

function update() {
    let point;
    for (let i = 0; i < POINTS.length; i++) {
        point = POINTS[i];
        point.move();
    }
}

function draw() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    let point;
    for (let i = 0; i < POINTS.length; i++) {
        point = POINTS[i];
        ctx.fillStyle = "rgba(" + point.r + "," + point.g + "," + point.b + "," + point.a + ")";
        ctx.beginPath();
        ctx.arc(point.getX(), point.getY(), SIZE, 0, 2 * Math.PI);
        ctx.fill();
    }

    window.requestAnimationFrame(animate);
}

init();