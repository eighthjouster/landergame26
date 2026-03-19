// Game configuration
const config = {
  type: Phaser.AUTO,
  width: 800,
  height: 600,
  physics: {
    default: 'arcade',
    arcade: {
      gravity: { y: 0 },
      debug: false
    }
  },
  scene: {
    preload: preload,
    create: create,
    update: update
  }
};

let lander;
let cursors;
let thrust;
let landerSpeed = 200;

function preload() {
  this.load.image('background', 'assets/space_background.png');
  this.load.image('lander', 'assets/lunar_lander.png');
}

function create() {
  this.add.image(400, 300, 'background');

  // Create the lunar lander sprite
  lander = this.physics.add.sprite(400, 100, 'lander');
  lander.setDamping(true);
  lander.setDrag(0.99);
  lander.setMaxVelocity(200);

  // Add controls
  cursors = this.input.keyboard.createCursorKeys();
}

function update() {
  // Basic movement using arrow keys
  if (cursors.left.isDown) {
    lander.setAngularVelocity(-100);
  }
  else if (cursors.right.isDown) {
    lander.setAngularVelocity(100);
  }
  else {
    lander.setAngularVelocity(0);
  }

  if (cursors.up.isDown) {
    this.physics.velocityFromRotation(lander.rotation, landerSpeed, thrust);
    lander.setVelocity(thrust.x, thrust.y);
  }
  else {
    lander.setVelocity(0, 0);
  }

  // Update the lander's position based on the physics engine
  lander.body.velocity.x *= 0.99;
  lander.body.velocity.y *= 0.99;
}

// Start the game
const game = new Phaser.Game(config);
