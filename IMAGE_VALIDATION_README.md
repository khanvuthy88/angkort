# Image Validation in Shop Controller

## Overview

The `_handle_shop_related_fields` method in the `e_menu/controllers/shop.py` file has been enhanced to include comprehensive image validation for the `image_1920` field, as well as improved validation for existing image fields like `shop_banner`.

## New Features

### 1. Image 1920 Field Support

The method now handles the `image_1920` field, which is commonly used for profile images in Odoo models. This field is automatically processed when included in form data or file uploads.

### 2. Enhanced Image Validation

All image fields now undergo comprehensive validation including:

- **File Size Validation**: Configurable maximum file size limits
  - `image_1920`: 5MB limit
  - `shop_banner`: 10MB limit

- **File Format Validation**: Only allows common image formats
  - Supported formats: `.jpg`, `.jpeg`, `.png`, `.gif`, `.bmp`, `.webp`

- **Image Dimension Validation**:
  - Minimum dimensions: 50x50 pixels
  - Maximum dimensions: 4096x4096 pixels
  - Aspect ratio limits: Between 0.1 and 10 (prevents extremely wide/tall images)

- **Content Validation**: Uses PIL (Pillow) to verify the image is valid and not corrupted

## Usage

### Basic Usage

The method automatically processes image fields when they are present in the request:

```python
# The method is called internally by shop creation/update endpoints
shop_related_fields = self._handle_shop_related_fields(data, files, 'create')
```

### Field Processing

The method processes the following fields:

1. **`image_1920`**: Profile image (5MB limit)
2. **`shop_banner`**: Shop banner image (10MB limit)
3. **`shop_wifi_ids`**: WiFi configuration (JSON array)
4. **`shop_open_hour_ids`**: Operating hours (JSON array)

### Error Handling

Image validation errors are logged but don't fail the entire operation. This allows the shop creation/update to proceed even if image validation fails.

## Configuration

### PARTNER_FIELDS Update

The `PARTNER_FIELDS` constant has been updated to include `image_1920`:

```python
PARTNER_FIELDS = [
    'name', 'wifi_name', 'phone', 'customer_address', 'shop_latitude', 'shop_longitude', 'email',
    'shop_banner', 'shop_wifi_ids', 'shop_open_hour_ids', 'image_1920'
]
```

### Dependencies

Added `Pillow>=9.0.0` to `requirements.txt` for image processing capabilities.

## Validation Rules

### Image 1920 (Profile Image)
- **Max Size**: 5MB
- **Min Dimensions**: 50x50 pixels
- **Max Dimensions**: 4096x4096 pixels
- **Aspect Ratio**: 0.1 to 10
- **Formats**: jpg, jpeg, png, gif, bmp, webp

### Shop Banner
- **Max Size**: 10MB
- **Min Dimensions**: 50x50 pixels
- **Max Dimensions**: 4096x4096 pixels
- **Aspect Ratio**: 0.1 to 10
- **Formats**: jpg, jpeg, png, gif, bmp, webp

## Testing

A test script `test_image_validation.py` is provided to verify the validation logic:

```bash
python test_image_validation.py
```

The test script creates various test images and validates them against the same rules used in the controller.

## API Endpoints

The enhanced validation is automatically applied to these endpoints:

- `POST /angkort/api/v1/shop` - Shop creation
- `PUT /angkort/api/v1/shop/<shop_id>` - Shop update

## Error Messages

Common validation error messages:

- `"image_1920: File size exceeds 5MB limit"`
- `"image_1920: Invalid file format. Allowed: .jpg, .jpeg, .png, .gif, .bmp, .webp"`
- `"image_1920: Image dimensions too small. Minimum: 50x50px"`
- `"image_1920: Image dimensions too large. Maximum: 4096x4096px"`
- `"image_1920: Image aspect ratio too extreme. Keep between 0.1 and 10"`

## Security Considerations

- File size limits prevent DoS attacks through large file uploads
- Format validation prevents malicious file uploads
- Dimension limits prevent memory exhaustion
- Aspect ratio limits prevent unusual image shapes that might cause display issues

## Future Enhancements

Potential improvements that could be added:

1. **Image Compression**: Automatic resizing of large images
2. **Format Conversion**: Convert to WebP for better performance
3. **Watermarking**: Add watermarks to uploaded images
4. **Virus Scanning**: Integrate with antivirus services
5. **Metadata Stripping**: Remove EXIF data for privacy
