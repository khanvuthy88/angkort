# Prompt for Stitch (http://stitch.withgoogle.com)

**Copy and paste the following prompt into Stitch to generate the merchant web application:**

```text
Design a comprehensive, modern Merchant Web Application (Dashboard) for "Angkort Shop", a food and beverage ordering platform. The design should feel premium, dynamic, and use a clean, glassmorphism-inspired aesthetic with a curated color palette (e.g., sleek dark mode with vibrant accent colors like amber or teal). 

The webapp is for merchants (restaurant/cafe owners) to manage their shops and should include the following core screens and components:

1. **Authentication Flow (Login & Register)**:
   - A clean, modern login screen requiring `username` and `password`.
   - A registration screen collecting `name`, `username`, and `password`.
   - Use dynamic hover effects on buttons and smooth transitions.

2. **Dashboard / Home Overview**:
   - A high-level overview showing today's stats (Sales, Active Orders).
   - A sidebar navigation menu with links to: Dashboard, Shop Profile, Menu (Products), Orders, and Settings.

3. **Shop Profile Management**:
   - A form layout to update shop details: `name`, `phone`, `customer_address`, `email`.
   - Sections to upload a `shop_banner` (image upload component) and set a map location (`shop_latitude`, `shop_longitude`).
   - A section to manage WiFi credentials (list of networks with `name`, `password`, and a QR code upload).
   - A weekly schedule component to set Open/Close hours for each day (Monday to Sunday).

4. **Menu & Product Management**:
   - A data grid or card-based layout listing all products with their images, categories, and prices.
   - An "Add Product" modal or page supporting form inputs for `name`, `description`, `sale_price`, and image upload.
   - A dedicated UI for managing **Variants and Attributes**: e.g., an area to define "Size" (Small, Large) and assign an `extra_price` to specific variant values.

5. **Order Management Interface**:
   - A Kanban-style board or a real-time list view for incoming orders.
   - Order cards displaying the `customer` info, order notes, and detailed line items (including specific variants chosen by the customer, like "Size: Large" or "Addons: Extra shot").
   - Action buttons to accept, complete, or reject orders.

The overall UI should prioritize visual excellence, using modern typography (e.g., Inter or Outfit), smooth gradients, and micro-animations for interactive elements. Ensure it looks like a state-of-the-art SaaS merchant dashboard.
```
