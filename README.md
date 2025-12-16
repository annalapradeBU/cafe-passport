# cafe_passport
A personalized digital "passport" and tracking application for coffee enthusiasts. Users can log their café visits with photos, notes, and favorite items, manage a dynamic wishlist, and visualize their habits through data analytics and interactive media customization.

> **Note:** This repository includes models, complex views, formsets, and templates to demonstrate the app's functionality, but does not include project-level configuration or sensitive backend code.

## Demo Video 
[Click Here to See Cafe Passport in Action!](https://youtu.be/huZhYfjc6U4)


---

**Author:** Anna LaPrade
**Contact:** [anna.m.laprade@gmail.com](mailto:anna.m.laprade@gmail.com)
**Date Started:** 2025-11-24

---

## Features

### ☕ **Core Functionality**

* **Transactional Visit Logging:** Securely log a café visit, including date, rating, and spending.
* **Complex Data Entry:** Log one visit simultaneously with multiple related media objects (Visit Photos, Favorite Items, and Item Photos) using **nested formsets** within a single, atomic submission. 
* **Personalized Profile:** View a dashboard showing visit history, wishlist status, and access to statistics.
* **Wishlist Management:** Add cafés to a dynamic wishlist; the system checks and visually marks if a wishlisted café has already been visited.
* **Advanced Café Search:** Search by name/address and filter results by applying **multiple tags** simultaneously (AND logic).

### ✨ **Interactive UX & Customization**

* **Dynamic Media Manipulation:** Utilizes JavaScript/Interact.js to allow users to **drag, drop, resize, and rotate** dynamic "stickers" onto visit photos. All transformation data (position, scale, rotation) is saved and retrieved via dedicated AJAX endpoints. 
* **AJAX-Driven Deletion:** Stickers can be deleted instantly via the keyboard (Backspace/Delete) with persistent removal handled asynchronously.
* **Theming System:** Users can select and instantly apply one of seven distinct themes (e.g., 'Gothic', 'Roastery') for a personalized experience, saved persistently via AJAX.

### 📊 **Data Visualization & Analytics**

* **User Statistics:** Dedicated dashboard (`CafeStatsView`) calculates and displays user analytics, including average spending, average visit rating, and wishlist conversion rate.
* **Plotly Integration:** Generates interactive **Pie Charts** using Plotly to visualize the distribution of tags across the user's visited cafés, providing clear insight into their preferences.

---

## Tech Stack

* **Backend:** Python, **Django (Class-Based Views, Complex Formsets, Advanced ORM)**
* **Frontend:** HTML5, CSS3, **Vanilla JavaScript (ES6), AJAX**
* **Database:** SQLite (default for development)
* **Libraries:** **Interact.js** (for dynamic UI manipulation), **Plotly** (for data visualization), **Select2** (for enhanced form inputs)

---

## Usage

1. **Explore Cafés:** View all available cafés or use the advanced search to find a new spot.
2. **Log a Visit:** Initiate a new visit entry for a café, filling out all details, including nested photos and favorite items, in one secure process.
3. **Customize Media:** On the `Visit Detail` page, use the sticker palette to dynamically decorate your photos.
4. **Track Progress:** Monitor your visiting habits and wishlist conversion on the **Cafe Stats** and **My Passport** pages.


