// 水平左右流出距离

class ParticleText {
    constructor(containerId, options = {}) {
        this.container = document.getElementById(containerId);
        this.options = {
            color: options.color || '#65B4C9',
            fontSize: options.fontSize || (window.innerWidth * 0.08),
            particleAmount: options.particleAmount || 6000,
            particleSize: options.particleSize || 2,
            initialDisplacement: options.initialDisplacement || 500,
            initialVelocity: options.initialVelocity || 7.5,
            velocityRetention: options.velocityRetention || 0.95,
            initialEffect: options.initialEffect || 'explode', // 新增初始特效参数
            settleSpeed: options.settleSpeed || 0.7,
            fleeSpeed: options.fleeSpeed || 0.5,
            fleeDistance: options.fleeDistance || 50,
            flee: options.flee !== undefined ? options.flee : true,
            scatterVelocity: options.scatterVelocity || 3,
            scatter: options.scatter !== undefined ? options.scatter : true
        };

        // 移动设备适配
        if (/Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent)) {
            this.options.fontSize = 50;
            this.options.particleAmount = 300;
            this.options.initialDisplacement = 100;
            this.options.settleSpeed = 1;
            this.options.flee = false;
            this.options.scatterVelocity = 2;
        }

        this.points = [];
        this.mouse = { x: 0, y: 0 };
        this.message = '';
        this.setupCanvas();
        this.bindEvents();
    }

    setupCanvas() {
        this.canvas = document.createElement('canvas');
        this.ctx = this.canvas.getContext('2d');
        this.container.appendChild(this.canvas);
        this.resizeCanvas();
    }

    resizeCanvas() {
        this.canvas.width = this.container.clientWidth;
        this.canvas.height = this.container.clientHeight;
    }

    bindEvents() {
        window.addEventListener('resize', () => {
            this.resizeCanvas();
            if (this.message) {
                this.setText(this.message);
            }
        });

        this.canvas.addEventListener('mousemove', (e) => {
            const rect = this.canvas.getBoundingClientRect();
            this.mouse.x = e.clientX - rect.left;
            this.mouse.y = e.clientY - rect.top;
        });
    }

    setText(text, options = {}) {
        this.message = text;
        this.ctx.font = `${this.options.fontSize}px "仓耳玉楷", sans-serif`;
        this.ctx.textAlign = 'center';
        this.ctx.textBaseline = 'middle';
        
        const textMetrics = this.ctx.measureText(text);
        const textWidth = textMetrics.width;
        const textHeight = this.options.fontSize;

        // 创建离屏canvas来获取像素数据
        const offscreenCanvas = document.createElement('canvas');
        const offscreenCtx = offscreenCanvas.getContext('2d');
        offscreenCanvas.width = textWidth;
        offscreenCanvas.height = textHeight * 1.5;

        offscreenCtx.font = this.ctx.font;
        offscreenCtx.textAlign = 'center';
        offscreenCtx.textBaseline = 'middle';
        offscreenCtx.fillStyle = '#ffffff';
        offscreenCtx.fillText(text, offscreenCanvas.width / 2, offscreenCanvas.height / 2);

        const imageData = offscreenCtx.getImageData(0, 0, offscreenCanvas.width, offscreenCanvas.height);
        this.points = [];

        for (let i = 0; i < this.options.particleAmount; i++) {
            let x, y;
            do {
                x = Math.floor(Math.random() * offscreenCanvas.width);
                y = Math.floor(Math.random() * offscreenCanvas.height);
            } while (!this.isPixelVisible(imageData, x, y));

            const initialEffect = options.initialEffect || this.options.initialEffect;

            if (initialEffect === 'explode') {
                this.points.push(new Point(
                    x - offscreenCanvas.width / 2,
                    y - offscreenCanvas.height / 2,
                    this.canvas,
                    { ...this.options, initialDisplacement: 100 }
                ));
            } else if (initialEffect === 'smooth') {
                this.points.push(new Point(
                    x - offscreenCanvas.width / 2,
                    y - offscreenCanvas.height / 2,
                    this.canvas,
                    { ...this.options, initialDisplacement: 3 } // 平滑初始特效
                ));
            }
        }

        if (!this.isAnimating) {
            this.animate();
        }
    }


    isPixelVisible(imageData, x, y) {
        const index = (y * imageData.width + x) * 4;
        return imageData.data[index + 3] > 128;
    }

    animate() {
        this.isAnimating = true;
        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
        
        for (const point of this.points) {
            point.update(this.mouse);
            point.draw(this.ctx);
        }

        requestAnimationFrame(() => this.animate());
    }
}

class Point {
    constructor(x, y, canvas, options) {
        const angle = Math.random() * 6.28;
        this.canvas = canvas;
        this.options = options;
        
        // 修正x和y坐标的计算方式，使文字正向显示且不镜像
        this.x = canvas.width / 2 + x + (Math.random() - 0.5) * options.initialDisplacement;
        this.y = canvas.height / 2 + y + (Math.random() - 0.5) * options.initialDisplacement;
        this.velx = options.initialVelocity * Math.cos(angle);
        this.vely = options.initialVelocity * Math.sin(angle);
        this.target_x = canvas.width / 2 + x;
        this.target_y = canvas.height / 2 + y;
    }

    distanceToMouse(mouse) {
        return Math.sqrt(Math.pow(mouse.x - this.x, 2) + Math.pow(mouse.y - this.y, 2));
    }

    update(mouse) {
        if (this.options.flee && this.distanceToMouse(mouse) <= this.options.fleeDistance) {
            this.velx -= ((mouse.x - this.x) * this.options.fleeSpeed / 10);
            this.vely -= ((mouse.y - this.y) * this.options.fleeSpeed / 10);
        }

        this.velx += ((this.target_x - this.x) * this.options.settleSpeed / 100);
        this.vely += ((this.target_y - this.y) * this.options.settleSpeed / 100);
        this.velx *= this.options.velocityRetention;
        this.vely *= this.options.velocityRetention;

        this.x += this.velx;
        this.y += this.vely;
    }

    draw(ctx) {
        ctx.fillStyle = this.options.color;
        ctx.beginPath();
        ctx.arc(this.x, this.y, this.options.particleSize, 0, Math.PI * 2);
        ctx.fill();
    }
}

// 导出ParticleText类
export default ParticleText;