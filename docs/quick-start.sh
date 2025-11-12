#!/bin/bash

# JiETNG 文档快速启动脚本
# 用于快速预览和构建文档

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印带颜色的消息
print_info() {
    echo -e "${BLUE}ℹ ${NC}$1"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

# 检查Node.js是否安装
check_nodejs() {
    if ! command -v node &> /dev/null; then
        print_error "Node.js未安装！"
        echo "请访问 https://nodejs.org/ 下载并安装Node.js 18+版本"
        exit 1
    fi

    NODE_VERSION=$(node -v | cut -d'v' -f2 | cut -d'.' -f1)
    if [ "$NODE_VERSION" -lt 18 ]; then
        print_error "Node.js版本过低（当前: $(node -v)）"
        echo "需要Node.js 18或更高版本"
        exit 1
    fi

    print_success "Node.js版本: $(node -v)"
}

# 检查npm权限
check_npm_permissions() {
    if [ -d "$HOME/.npm" ]; then
        if [ ! -w "$HOME/.npm" ]; then
            print_warning "npm缓存目录权限不足"
            echo "正在尝试修复..."

            # 尝试修复权限
            if sudo -n chown -R $(id -u):$(id -g) "$HOME/.npm" 2>/dev/null; then
                print_success "权限已修复"
            else
                print_warning "需要手动修复权限，请运行："
                echo "  sudo chown -R $(id -u):$(id -g) \"$HOME/.npm\""
                echo ""
                read -p "按回车键继续，或Ctrl+C退出..."
            fi
        fi
    fi
}

# 安装依赖
install_deps() {
    print_info "检查依赖..."

    if [ ! -d "node_modules" ]; then
        print_info "安装依赖中... (这可能需要1-2分钟)"
        npm install
        print_success "依赖安装完成"
    else
        print_success "依赖已安装"
    fi
}

# 清除缓存
clean_cache() {
    print_info "清除缓存..."
    rm -rf .vitepress/cache
    rm -rf .vitepress/dist
    print_success "缓存已清除"
}

# 开发模式
dev_mode() {
    print_info "启动开发服务器..."
    echo ""
    print_success "开发服务器即将启动"
    echo "  按 Ctrl+C 停止服务器"
    echo ""
    npm run docs:dev
}

# 构建模式
build_mode() {
    print_info "构建生产版本..."
    npm run docs:build
    print_success "构建完成！"
    echo "  输出目录: .vitepress/dist/"
}

# 预览模式
preview_mode() {
    print_info "预览生产构建..."

    if [ ! -d ".vitepress/dist" ]; then
        print_warning "尚未构建，先执行构建..."
        build_mode
    fi

    echo ""
    print_success "预览服务器即将启动"
    echo "  按 Ctrl+C 停止服务器"
    echo ""
    npm run docs:preview
}

# 显示帮助
show_help() {
    echo "JiETNG 文档快速启动脚本"
    echo ""
    echo "用法: ./quick-start.sh [选项]"
    echo ""
    echo "选项:"
    echo "  dev       启动开发服务器（热重载）"
    echo "  build     构建生产版本"
    echo "  preview   预览生产构建"
    echo "  clean     清除缓存"
    echo "  help      显示此帮助信息"
    echo ""
    echo "示例:"
    echo "  ./quick-start.sh dev       # 开发模式"
    echo "  ./quick-start.sh build     # 构建"
    echo "  ./quick-start.sh preview   # 预览"
    echo ""
}

# 主函数
main() {
    # 进入docs目录
    cd "$(dirname "$0")"

    echo "================================================"
    echo "   JiETNG 文档快速启动"
    echo "================================================"
    echo ""

    # 基础检查
    check_nodejs
    check_npm_permissions

    # 根据参数执行操作
    case "${1:-dev}" in
        dev)
            install_deps
            dev_mode
            ;;
        build)
            install_deps
            build_mode
            ;;
        preview)
            install_deps
            preview_mode
            ;;
        clean)
            clean_cache
            print_success "完成！"
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            print_error "未知选项: $1"
            echo ""
            show_help
            exit 1
            ;;
    esac
}

# 运行主函数
main "$@"
