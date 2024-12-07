class Starfield {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        this.canvas = document.createElement('canvas');
        this.ctx = this.canvas.getContext('2d');
        this.stars = [];
        this.numberOfStars = 200;
        this.fps = 60;
        this.init();
    }

    init() {
        this.setupCanvas();
        this.createStars();
        this.animate();
        window.addEventListener('resize', () => this.setupCanvas());
    }

    setupCanvas() {
        this.width = this.container.offsetWidth;
        this.height = this.container.offsetHeight;
        this.canvas.width = this.width;
        this.canvas.height = this.height;
        this.container.appendChild(this.canvas);
    }

    createStars() {
        this.stars = [];
        for (let i = 0; i < this.numberOfStars; i++) {
            this.stars.push({
                x: Math.random() * this.width,
                y: Math.random() * this.height,
                size: Math.random() * 2,
                speed: Math.random() * 0.5
            });
        }
    }

    moveStars() {
        this.stars.forEach(star => {
            star.y += star.speed;
            if (star.y > this.height) {
                star.y = 0;
                star.x = Math.random() * this.width;
            }
        });
    }

    drawStars() {
        this.ctx.clearRect(0, 0, this.width, this.height);
        this.ctx.fillStyle = '#FFF';
        this.stars.forEach(star => {
            this.ctx.beginPath();
            this.ctx.arc(star.x, star.y, star.size, 0, Math.PI * 2);
            this.ctx.fill();
        });
    }

    animate() {
        this.moveStars();
        this.drawStars();
        setTimeout(() => {
            requestAnimationFrame(() => this.animate());
        }, 1000 / this.fps);
    }
}
