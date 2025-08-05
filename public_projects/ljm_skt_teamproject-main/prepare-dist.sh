#!/bin/bash

# Remove old dist
rm -rf dist

# Build with Expo
npx expo export --platform web --output-dir dist

# Copy assets to root for direct access
cd dist
cp -f assets/assets/*.gif . 2>/dev/null || true
cp -f assets/assets/*.svg . 2>/dev/null || true
cp -f assets/assets/images/*.png . 2>/dev/null || true
cp -f assets/node_modules/@expo/vector-icons/build/vendor/react-native-vector-icons/Fonts/*.ttf . 2>/dev/null || true

echo "Build prepared for deployment!"