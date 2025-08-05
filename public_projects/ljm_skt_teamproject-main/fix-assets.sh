#!/bin/bash

# Create symbolic links to fix asset paths
cd dist

# Create root-level links for assets that are being requested without /assets/assets/ prefix
ln -sf assets/assets/yammi_welcome.72ba19e3fc6bc067ad5255a68806922c.gif yammi_welcome.72ba19e3fc6bc067ad5255a68806922c.gif
ln -sf assets/assets/yammi_think.f89d14fa4c0417e314e104a02c220197.gif yammi_think.f89d14fa4c0417e314e104a02c220197.gif
ln -sf assets/assets/yammi_tmp.37791cbf4f2b698134c7f65c1bd65bd8.gif yammi_tmp.37791cbf4f2b698134c7f65c1bd65bd8.gif
ln -sf assets/assets/yammi_waiting.41379fa649d73e030fd5a98eea638936.gif yammi_waiting.41379fa649d73e030fd5a98eea638936.gif
ln -sf assets/assets/settings.60d6b196056ee6505a698db852efcf70.svg settings.60d6b196056ee6505a698db852efcf70.svg
ln -sf assets/assets/images/chat-button.3c45e652753fd3a926400008072617ef.png chat-button.3c45e652753fd3a926400008072617ef.png

# Create links for fonts
ln -sf assets/node_modules/@expo/vector-icons/build/vendor/react-native-vector-icons/Fonts/Ionicons.6148e7019854f3bde85b633cb88f3c25.ttf Ionicons.6148e7019854f3bde85b633cb88f3c25.ttf

echo "Asset links created!"