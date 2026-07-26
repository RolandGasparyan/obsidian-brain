# Mercury AI Design System

**Parent Project:** [[Mercury AI Assistant - Project Hub]]**Design URL:** https://claude.ai/design/p/dcaf5600-f940-40fe-b868-9d07b323ad70
**Last Updated:** 2026-07-24
**Version:** 1.0

---

## 🎨 Design Overview

Mercury AI Assistant features a modern, clean design system built for intuitive user interaction and seamless AI integration. This design system documents all visual components, color schemes, typography, and interactive patterns.

---

## 📐 Design Tokens

### Color Palette

#### Primary Colors
| Token                                                                                                 | Color | Hex | Usage |
| ----------------------------------------------------------------------------------------------------- | ----- | --- | ----- |
| ary Brand \| Blue \| `#007AFF` \| Main CTA, Links, Highlights \|Prim                                  |       |     |       |
| \| Primary Dark \| Dark Blue \| `#0051D5` \| Hover states, Active states \|                           |       |     |       |
| \| Primary Light \| Light Blue \| `#E3F2FD` \| Backgrounds, Disabled states \|                        |       |     |       |
|                                                                                                       |       |     |       |
| #### Neutral Colors                                                                                   |       |     |       |
| \| Token \| Color \| Hex \| Usage \|                                                                  |       |     |       |
| \|-------\|-------\|-----\|-------\|                                                                  |       |     |       |
| \| Text Primary \| Dark Gray \| `#1F2937` \| Main text, Headings \|                                   |       |     |       |
| \| Text Secondary \| Medium Gray \| `#6B7280` \| Secondary text, Labels \|                            |       |     |       |
| \| Text Tertiary \| Light Gray \| `#9CA3AF` \| Disabled text, Hints \|                                |       |     |       |
| \| Background \| White \| `#FFFFFF` \| Main backgrounds \|                                            |       |     |       |
| \| Surface \| Light Gray \| `#F9FAFB` \| Card backgrounds \|                                          |       |     |       |
| \| Border \| Border Gray \| `#E5E7EB` \| Borders, Dividers \|                                         |       |     |       |
|                                                                                                       |       |     |       |
| #### Status Colors                                                                                    |       |     |       |
| \| Token \| Color \| Hex \| Usage \|                                                                  |       |     |       |
| \|-------\|-------\|-----\|-------\|                                                                  |       |     |       |
| \| Success \| Green \| `#10B981` \| Success messages, Checkmarks \|                                   |       |     |       |
| \| Warning \| Amber \| `#F59E0B` \| Warnings, Alerts \|                                               |       |     |       |
| \| Error \| Red \| `#EF4444` \| Errors, Destructive actions \|                                        |       |     |       |
| \| Info \| Cyan \| `#06B6D4` \| Info messages, Tips \|                                                |       |     |       |
|                                                                                                       |       |     |       |
| ### Typography                                                                                        |       |     |       |
|                                                                                                       |       |     |       |
| #### Font Family                                                                                      |       |     |       |
| - **Primary Font:** `Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif`                |       |     |       |
| - **Monospace Font:** `'Courier New', 'Courier', monospace`                                           |       |     |       |
|                                                                                                       |       |     |       |
| #### Font Sizes                                                                                       |       |     |       |
| \| Token \| Size \| Line Height \| Usage \|                                                           |       |     |       |
| \|-------\|------\|-------------\|-------\|                                                           |       |     |       |
| \| Display \| 48px \| 1.2 \| Page titles, H1 \|                                                       |       |     |       |
| \| Heading 1 \| 36px \| 1.25 \| Section headers, H2 \|                                                |       |     |       |
| \| Heading 2 \| 28px \| 1.3 \| Subsections, H3 \|                                                     |       |     |       |
| \| Heading 3 \| 24px \| 1.35 \| Cards, H4 \|                                                          |       |     |       |
| \| Body Large \| 18px \| 1.6 \| Large text \|                                                         |       |     |       |
| \| Body \| 16px \| 1.6 \| Default text \|                                                             |       |     |       |
| \| Body Small \| 14px \| 1.5 \| Secondary text \|                                                     |       |     |       |
| \| Caption \| 12px \| 1.4 \| Labels, Captions \|                                                      |       |     |       |
| \| Code \| 13px \| 1.5 \| Code blocks \|                                                              |       |     |       |
|                                                                                                       |       |     |       |
| #### Font Weights                                                                                     |       |     |       |
| - Light: 300                                                                                          |       |     |       |
| - Regular: 400                                                                                        |       |     |       |
| - Medium: 500                                                                                         |       |     |       |
| - Semibold: 600                                                                                       |       |     |       |
| - Bold: 700                                                                                           |       |     |       |
|                                                                                                       |       |     |       |
| ### Spacing Scale                                                                                     |       |     |       |
| ```<br>```                                                                                            |       |     |       |
| 2px.  - xs                                                                                            |       |     |       |
| 4px.  - sm                                                                                            |       |     |       |
| 8px.  - base                                                                                          |       |     |       |
| 12px. - md                                                                                            |       |     |       |
| 16px. - lg                                                                                            |       |     |       |
| 24px. - xl                                                                                            |       |     |       |
| 32px. - 2xl                                                                                           |       |     |       |
| 48px. - 3xl                                                                                           |       |     |       |
| 64px. - 4xl                                                                                           |       |     |       |
| ```<br>```                                                                                            |       |     |       |
|                                                                                                       |       |     |       |
| ### Shadows                                                                                           |       |     |       |
|                                                                                                       |       |     |       |
| \| Token \| Shadow \| Usage \|                                                                        |       |     |       |
| \|-------\|--------\|-------\|                                                                        |       |     |       |
| \| Elevation 1 \| `0 1px 2px rgba(0,0,0,0.05)` \| Subtle shadows, borders \|                          |       |     |       |
| \| Elevation 2 \| `0 4px 6px rgba(0,0,0,0.07)` \| Card shadows \|                                     |       |     |       |
| \| Elevation 3 \| `0 10px 15px rgba(0,0,0,0.1)` \| Floating elements \|                               |       |     |       |
| \| Elevation 4 \| `0 20px 25px rgba(0,0,0,0.1)` \| Modals, Dropdowns \|                               |       |     |       |
|                                                                                                       |       |     |       |
| ### Border Radius                                                                                     |       |     |       |
|                                                                                                       |       |     |       |
| \| Token \| Value \| Usage \|                                                                         |       |     |       |
| \|-------\|-------\|-------\|                                                                         |       |     |       |
| \| None \| 0 \| Sharp corners \|                                                                      |       |     |       |
| \| Small \| 4px \| Small elements \|                                                                  |       |     |       |
| \| Base \| 8px \| Default radius \|                                                                   |       |     |       |
| \| Medium \| 12px \| Cards, Input fields \|                                                           |       |     |       |
| \| Large \| 16px \| Larger components \|                                                              |       |     |       |
| \| Full \| 9999px \| Pills, Avatars \|                                                                |       |     |       |
|                                                                                                       |       |     |       |
| ---                                                                                                   |       |     |       |
|                                                                                                       |       |     |       |
| ## 🧩 Component Library                                                                               |       |     |       |
|                                                                                                       |       |     |       |
| ### Buttons                                                                                           |       |     |       |
|                                                                                                       |       |     |       |
| #### Primary Button                                                                                   |       |     |       |
| - **Background:** Primary Blue (`#007AFF`)                                                            |       |     |       |
| - **Text Color:** White                                                                               |       |     |       |
| - **Padding:** 12px 24px                                                                              |       |     |       |
| - **Border Radius:** 8px                                                                              |       |     |       |
| - **Font Weight:** 600                                                                                |       |     |       |
| - **Hover State:** Darken to `#0051D5`                                                                |       |     |       |
| - **Active State:** Darker still, Shadow Elevation 2                                                  |       |     |       |
| - **Disabled State:** Gray background, 50% opacity                                                    |       |     |       |
|                                                                                                       |       |     |       |
| #### Secondary Button                                                                                 |       |     |       |
| - **Background:** Surface Gray (`#F9FAFB`)                                                            |       |     |       |
| - **Text Color:** Primary Blue (`#007AFF`)                                                            |       |     |       |
| - **Border:** 1px solid Border Gray                                                                   |       |     |       |
| - **Padding:** 12px 24px                                                                              |       |     |       |
| - **Border Radius:** 8px                                                                              |       |     |       |
| - **Hover State:** Background becomes `#E3F2FD`                                                       |       |     |       |
|                                                                                                       |       |     |       |
| #### Text Button                                                                                      |       |     |       |
| - **Background:** Transparent                                                                         |       |     |       |
| - **Text Color:** Primary Blue                                                                        |       |     |       |
| - **Padding:** 8px 16px                                                                               |       |     |       |
| - **Hover State:** Background `#E3F2FD`                                                               |       |     |       |
| - **Underline:** On hover                                                                             |       |     |       |
|                                                                                                       |       |     |       |
| ### Input Fields                                                                                      |       |     |       |
|                                                                                                       |       |     |       |
| #### Text Input                                                                                       |       |     |       |
| - **Background:** White                                                                               |       |     |       |
| - **Border:** 1px solid Border Gray                                                                   |       |     |       |
| - **Border Radius:** 8px                                                                              |       |     |       |
| - **Padding:** 12px 16px                                                                              |       |     |       |
| - **Font Size:** 16px                                                                                 |       |     |       |
| - **Focus State:** Border becomes Primary Blue, Shadow Elevation 1                                    |       |     |       |
| - **Error State:** Border becomes Error Red, Error icon appears                                       |       |     |       |
|                                                                                                       |       |     |       |
| #### Text Area                                                                                        |       |     |       |
| - **Same as Text Input but allow multi-line**                                                         |       |     |       |
| - **Min Height:** 120px                                                                               |       |     |       |
| - **Resize:** Vertical                                                                                |       |     |       |
|                                                                                                       |       |     |       |
| ### Cards                                                                                             |       |     |       |
|                                                                                                       |       |     |       |
| #### Default Card                                                                                     |       |     |       |
| - **Background:** White                                                                               |       |     |       |
| - **Border:** 1px solid Border Gray                                                                   |       |     |       |
| - **Border Radius:** 12px                                                                             |       |     |       |
| - **Padding:** 20px                                                                                   |       |     |       |
| - **Shadow:** Elevation 1                                                                             |       |     |       |
| - **Hover State:** Shadow Elevation 2                                                                 |       |     |       |
|                                                                                                       |       |     |       |
| #### Interactive Card                                                                                 |       |     |       |
| - **Same as Default Card**                                                                            |       |     |       |
| - **Cursor:** Pointer                                                                                 |       |     |       |
| - **Hover State:** Background becomes `#F9FAFB`, Shadow Elevation 2                                   |       |     |       |
|                                                                                                       |       |     |       |
| ### Navigation                                                                                        |       |     |       |
|                                                                                                       |       |     |       |
| #### Top Navigation Bar                                                                               |       |     |       |
| - **Background:** White                                                                               |       |     |       |
| - **Height:** 64px                                                                                    |       |     |       |
| - **Padding:** 0 24px                                                                                 |       |     |       |
| - **Border Bottom:** 1px solid Border Gray                                                            |       |     |       |
| - **Shadow:** Elevation 1                                                                             |       |     |       |
| - **Sticky:** Yes                                                                                     |       |     |       |
|                                                                                                       |       |     |       |
| #### Sidebar Navigation                                                                               |       |     |       |
| - **Width:** 280px                                                                                    |       |     |       |
| - **Background:** `#F9FAFB`                                                                           |       |     |       |
| - **Active Item:** Left border 4px Primary Blue, Background `#E3F2FD`                                 |       |     |       |
| - **Hover Item:** Background becomes lighter                                                          |       |     |       |
|                                                                                                       |       |     |       |
| ---                                                                                                   |       |     |       |
|                                                                                                       |       |     |       |
| ## 🎭 UI Patterns                                                                                     |       |     |       |
|                                                                                                       |       |     |       |
| ### Forms                                                                                             |       |     |       |
| - **Label:** Above input, 14px bold                                                                   |       |     |       |
| - **Helper Text:** Below input, 12px secondary gray                                                   |       |     |       |
| - **Error Messages:** Below input, 12px error red                                                     |       |     |       |
| - **Required Field:** Asterisk (*) in red next to label                                               |       |     |       |
|                                                                                                       |       |     |       |
| ### Modals                                                                                            |       |     |       |
| - **Backdrop:** Black 40% opacity                                                                     |       |     |       |
| - **Dialog:** Center screen, max-width 600px                                                          |       |     |       |
| - **Border Radius:** 12px                                                                             |       |     |       |
| - **Padding:** 32px                                                                                   |       |     |       |
| - **Shadow:** Elevation 4                                                                             |       |     |       |
|                                                                                                       |       |     |       |
| ### Notifications/Toasts                                                                              |       |     |       |
| - **Success Toast:** Green background, white text                                                     |       |     |       |
| - **Error Toast:** Red background, white text                                                         |       |     |       |
| - **Warning Toast:** Amber background, white text                                                     |       |     |       |
| - **Info. Toast:**Cyan background, white text                                                         |       |     |       |
| - **Position:** Bottom right                                                                          |       |     |       |
| - **Auto Dismiss:** 5 seconds                                                                         |       |     |       |
|                                                                                                       |       |     |       |
| ### Loading States                                                                                    |       |     |       |
| - **Spinner:** 24px circular spinner, Primary Blue                                                    |       |     |       |
| - **Skeleton:** Gray placeholder, 200ms pulse animation                                               |       |     |       |
| - **Progress Bar:** Primary Blue, smooth animation                                                    |       |     |       |
|                                                                                                       |       |     |       |
| ---                                                                                                   |       |     |       |
|                                                                                                       |       |     |       |
| ## 📱 Responsive Breakpoints                                                                          |       |     |       |
|                                                                                                       |       |     |       |
| \| Breakpoint \| Width \| Device \|                                                                   |       |     |       |
| \|-----------\|-------\|--------\|                                                                    |       |     |       |
| \| Mobile \| 320px - 640px \| Phones \|                                                               |       |     |       |
| \| Tablet \| 641px - 1024px \| Tablets \|                                                             |       |     |       |
| \| Desktop \| 1025. x- 1536px \| Desktops \|                                                          |       |     |       |
| \| Large \| 1537px+ \| Large screens \|                                                               |       |     |       |
|                                                                                                       |       |     |       |
| ---                                                                                                   |       |     |       |
|                                                                                                       |       |     |       |
| ## ✏️Editable Assets                                                                                  |       |     |       |
|                                                                                                       |       |     |       |
| ### Logo Variations                                                                                   |       |     |       |
| - [ ] Main Logo (SVG)                                                                                 |       |     |       |
| - [ ] Logo Mark Only                                                                                  |       |     |       |
| - [ ] Logo Horizontal                                                                                 |       |     |       |
| - [ ] Logo Stacked                                                                                    |       |     |       |
| - [ ] Monochrome Version                                                                              |       |     |       |
|                                                                                                       |       |     |       |
| ### Icon Set                                                                                          |       |     |       |
| - [ ] Navigation Icons (24 icons)                                                                     |       |     |       |
| - [ ] Status Icons (12 icons)                                                                         |       |     |       |
| - [ ] Action Icons (20 icons)                                                                         |       |     |       |
| - [ ] Social Icons (8 icons)                                                                          |       |     |       |
|                                                                                                       |       |     |       |
| ### Backgrounds & Patterns                                                                            |       |     |       |
| - [ ] Hero Background                                                                                 |       |     |       |
| - [ ] Subtle Pattern (for sections)                                                                   |       |     |       |
| - [ ] Gradient Backgrounds (3 variants)                                                               |       |     |       |
| - [ ] Textures                                                                                        |       |     |       |
|                                                                                                       |       |     |       |
| ### Templates                                                                                         |       |     |       |
| - [ ] Landing Page Template                                                                           |       |     |       |
| - [ ] Dashboard Template                                                                              |       |     |       |
| - [ ] Form Page Template                                                                              |       |     |       |
| - [ ] Error Page Template                                                                             |       |     |       |
|                                                                                                       |       |     |       |
| ---                                                                                                   |       |     |       |
|                                                                                                       |       |     |       |
| ## 🔄 Design Handoff Checklist                                                                        |       |     |       |
|                                                                                                       |       |     |       |
| - [ ] All components documented                                                                       |       |     |       |
| - [ ] Color palette approved                                                                          |       |     |       |
| - [ ] Typography finalized                                                                            |       |     |       |
| - [ ] Spacing guidelines confirmed                                                                    |       |     |       |
| - [ ] Interactive states defined                                                                      |       |     |       |
| - [ ] Responsive behavior specified                                                                   |       |     |       |
| - [ ] Accessibility standards checked                                                                 |       |     |       |
| - [ ] Design system exported to Figma                                                                 |       |     |       |
| - [ ] Component library built                                                                         |       |     |       |
| - [ ] Developer documentation ready                                                                   |       |     |       |
|                                                                                                       |       |     |       |
| ---                                                                                                   |       |     |       |
|                                                                                                       |       |     |       |
| ## 📊 Asset Management                                                                                |       |     |       |
|                                                                                                       |       |     |       |
| ### Current Assets                                                                                    |       |     |       |
| - Total Components: 45+                                                                               |       |     |       |
| - Icon Set: Available                                                                                 |       |     |       |
| - Color Variants: 20+                                                                                 |       |     |       |
| - Responsive Layouts: 12+                                                                             |       |     |       |
|                                                                                                       |       |     |       |
| ### Asset Version Control                                                                             |       |     |       |
| \| Version \| Date \| Changes \|                                                                      |       |     |       |
| \|---------\|------\|---------\|                                                                      |       |     |       |
| \| 1.0 \| 2026-07-24 \| Initial design system \|                                                      |       |     |       |
| \| \| \| \|                                                                                           |       |     |       |
| \| \| \| \|                                                                                           |       |     |       |
|                                                                                                       |       |     |       |
| ### Export Formats                                                                                    |       |     |       |
| - [ ] Figma File (Primary)                                                                            |       |     |       |
| - [ ] Adobe XD                                                                                        |       |     |       |
| - [ ] Sketch                                                                                          |       |     |       |
| - [ ] CSS/SCSS Variables                                                                              |       |     |       |
| - [ ] PNG Assets (for web)                                                                            |       |     |       |
| - [ ] SVG Icons                                                                                       |       |     |       |
|                                                                                                       |       |     |       |
| ---                                                                                                   |       |     |       |
|                                                                                                       |       |     |       |
| ## 🔗 Related Resources                                                                               |       |     |       |
|                                                                                                       |       |     |       |
| - **Design Link:** [Claude Design - Mercury AI](https://claude.ai/design/p/dcaf5600-f940-40fe-b868-9) |       |     |       |