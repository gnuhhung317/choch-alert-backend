"""
Convert favicon.jpg to favicon.ico for better browser support
"""
try:
    from PIL import Image
    
    # Open JPG
    img = Image.open('web/static/images/favicon.jpg')
    
    # Convert to RGB if needed
    if img.mode != 'RGB':
        img = img.convert('RGB')
    
    # Resize to common favicon sizes and save as ICO
    img.save('web/static/images/favicon.ico', format='ICO', sizes=[(16, 16), (32, 32), (48, 48)])
    
    print("✅ Created favicon.ico with sizes: 16x16, 32x32, 48x48")
    print("📁 Location: web/static/images/favicon.ico")
    
except ImportError:
    print("❌ PIL/Pillow not installed. Install with: pip install Pillow")
except Exception as e:
    print(f"❌ Error: {e}")
