#!/usr/bin/env bash
set -e

echo "=== Building Tauri Application ==="

# Check prerequisites
if ! command -v cargo &> /dev/null; then
    echo "❌ Rust/Cargo not found. Install from https://rustup.rs/"
    exit 1
fi

if ! command -v node &> /dev/null; then
    echo "❌ Node.js not found. Install from https://nodejs.org/"
    exit 1
fi

if ! command -v npm &> /dev/null; then
    echo "❌ npm not found."
    exit 1
fi

echo "✅ Prerequisites check passed"

# Build Rust library
echo ""
echo "=== Building Rust library ==="
cargo build --lib --release
echo "✅ Rust library built successfully"

# Build Rust binary
echo ""
echo "=== Building Rust binary ==="
cargo build --bin myapp --release
echo "✅ Rust binary built successfully"

# Install frontend dependencies
echo ""
echo "=== Installing frontend dependencies ==="
npm install
echo "✅ Frontend dependencies installed"

# Build frontend
echo ""
echo "=== Building frontend ==="
npm run build
echo "✅ Frontend built successfully"

# Verify outputs
echo ""
echo "=== Verifying build outputs ==="
if [ -f "dist/index.html" ]; then
    echo "✅ Frontend output: dist/index.html"
else
    echo "❌ Frontend output not found: dist/index.html"
    exit 1
fi

if [ -f "target/release/myapp" ]; then
    echo "✅ Rust binary: target/release/myapp"
else
    echo "❌ Rust binary not found: target/release/myapp"
    exit 1
fi

# Show build stats
echo ""
echo "=== Build Statistics ==="
echo "Frontend size: $(du -sh dist/ | cut -f1)"
echo "Binary size: $(du -sh target/release/myapp | cut -f1)"
echo "Total source files: $(find src -name '*.rs' -o -name '*.ts' -o -name '*.tsx' | wc -l)"

echo ""
echo "🎉 Build completed successfully!"
echo ""
echo "To run the application:"
echo "  ./target/release/myapp"
echo ""
echo "To build with Tauri (requires full environment):"
echo "  npm run tauri build"
