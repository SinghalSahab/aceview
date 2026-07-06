# AceView Client Frontend 💻

This directory contains the Next.js frontend application for AceView.

For complete project documentation, overview, and setup guides, please refer to the main [Root README](../README.md).

## Quick Start (Frontend)

1. **Install Dependencies**:
   ```bash
   npm install
   ```

2. **Configure Environment Variables**:
   Create a `.env` file based on [.env.example](.env.example):
   ```bash
   cp .env.example .env
   ```

3. **Prisma Setup**:
   Ensure you run the Prisma client generation:
   ```bash
   npx prisma generate
   ```

4. **Run Development Server**:
   ```bash
   npm run dev
   ```
   Open [http://localhost:3000](http://localhost:3000) to view it in the browser.

## Build for Production

To build the client bundle for production deployment:
```bash
npm run build
npm run start
```
