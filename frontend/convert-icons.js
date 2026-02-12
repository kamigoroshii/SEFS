const sharp = require('sharp');
const fs = require('fs');

async function convertSvgToPng() {
  try {
    // Convert 192x192 icon
    await sharp('public/icon-192.svg')
      .resize(192, 192)
      .png()
      .toFile('public/icon-192.png');
    console.log('✓ Created icon-192.png');

    // Convert 512x512 icon
    await sharp('public/icon-512.svg')
      .resize(512, 512)
      .png()
      .toFile('public/icon-512.png');
    console.log('✓ Created icon-512.png');

    console.log('All icons converted successfully!');
  } catch (error) {
    console.error('Error converting icons:', error);
  }
}

convertSvgToPng();
