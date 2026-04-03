import sys
import pygame
import pygame.freetype
import random
import os
import math

# --- 1. 系统与引擎初始化 ---
# 强制标准输出使用 UTF-8 编码，防止在某些控制台下显示中文乱码
sys.stdout.reconfigure(encoding='utf-8')
pygame.init()           # 初始化 Pygame 核心逻辑
pygame.freetype.init()  # 初始化字体引擎，用于渲染 Emoji 和文字
pygame.mixer.init()     # 初始化音频混合器，用于播放音效

# --- 2. 全局静态配置 ---
CANVAS_WIDTH = 1500     # 游戏窗口宽度
CANVAS_HEIGHT = 1010    # 游戏窗口高度
COUNTDOWN_TIME = 300    # 总倒计时时间（300秒）

# 颜色定义 (RGB 格式)
WHITE = (255, 255, 255)
BLACK = (10, 10, 10)
GRAY_SLOT = (35, 35, 35)      # 卡片底部的阴影槽位颜色
BG_COLOR = (45, 55, 65)       # 游戏深蓝色背景
SELECTED_BORDER_COLOR = (255, 0, 0) # 选中时的红框颜色
SELECTED_BORDER_WIDTH = 4

# 随机图标颜色池，用于给不同的水果图标上色
COLORS = [(255, 165, 0), (0, 128, 0), (0, 0, 255), (128, 0, 128), (255, 20, 147),
          (255, 255, 0), (0, 255, 255), (128, 128, 0), (128, 0, 0), (0, 128, 128)]

# 系统字体路径
CHINESE_FONT = 'C:\\Windows\\Fonts\\msyh.ttc'   # 微软雅黑
EMOJI_FONT = 'C:\\Windows\\Fonts\\seguiemj.ttf' # Windows自带Emoji字体

# 辅助函数：安全加载字体，如果路径不存在则回退到 arial 字体
def get_font(path, size):
    try:
        if os.path.exists(path):
            return pygame.freetype.Font(path, size)
        return pygame.freetype.SysFont('arial', size)
    except:
        return pygame.freetype.SysFont('arial', size)

font_ui = get_font(CHINESE_FONT, 32) # 初始化 UI 字体

# 音频加载辅助函数
def load_sound(file):
    if os.path.exists(file): return pygame.mixer.Sound(file)
    return None

sound_click = load_sound('click.wav') # 点击音效
sound_match = load_sound('match.wav') # 消除音效

# --- 3. 卡片类 (Card Class) ---
# 将每张“羊”封装成一个对象，方便管理位置、状态和绘制
class Card:
    def __init__(self, x, y, icon, size, color, font):
        self.rect = pygame.Rect(x, y, size, size) # 定义卡片的矩形区域（碰撞检测用）
        self.icon = icon    # 存储图标内容（如 🍎）
        self.color = color  # 存储图标显示的颜色
        self.font = font    # 存储该卡片使用的字体大小
        self.selected = False # 选中状态，默认为 False

    def draw(self, surf):
        """将卡片绘制到指定的画布上"""
        # A. 绘制卡片白色背景，带圆角效果
        pygame.draw.rect(surf, WHITE, self.rect, border_radius=8)
        # B. 渲染 Emoji 文字图标
        text_surf, text_rect = self.font.render(self.icon, fgcolor=self.color)
        # C. 将图标对齐到卡片正中心
        text_rect.center = self.rect.center
        surf.blit(text_surf, text_rect)
        # D. 如果被选中，绘制红色边框
        if self.selected:
            pygame.draw.rect(surf, SELECTED_BORDER_COLOR, self.rect, SELECTED_BORDER_WIDTH, border_radius=8)

    def is_clicked(self, pos):
        """检测鼠标点击位置 pos 是否落在卡片矩形内"""
        return self.rect.collidepoint(pos)

# --- 4. 核心：关卡生成逻辑 ---
# 负责计算每一关的难度、卡片数量、排列方式
def create_level(level_num):
    icons_1 = ['🍎', '🍌', '🍇']
    icons_2 = ['🍎', '🍌', '🍇', '🍓', '🍒', '🥝', '🍍', '🍐', '🍊', '🍋']
    icons_3 = icons_2 + ['🍅', '🍆', '🥑', '🥦', '🌽']

    # 根据关卡号动态设定参数
    if level_num == 1:
        pool = icons_1
        cards_raw = icons_1 * 3 # 第一关：3种图标，每种3个，共9张
        cols, rows, size, gap = 3, 3, 130, 25 # 3x3 排列，卡片很大
    elif level_num == 2:
        pool = icons_2
        cards_raw = icons_2 * 30 # 第二关：10种图标，每种30个，共300张
        cols = 20
        rows = math.ceil(len(cards_raw) / cols) # 自动算出行数
        size, gap = 58, 6
    else:
        pool = icons_3
        cards_raw = icons_3 * 30 # 第三关：15种图标，每种30个，共450张
        cols = 25
        rows = math.ceil(len(cards_raw) / cols)
        size, gap = 48, 4 # 卡片更小更密集

    # 给该关卡出现的每种图标随机分配一种颜色
    icon_color_map = {icon: random.choice(COLORS) for icon in pool}
    random.shuffle(cards_raw) # 彻底打乱卡片顺序

    # 布局计算：计算整体阵列占用的总宽和总高，用于居中显示
    total_w = cols * (size + gap) - gap
    total_h = rows * (size + gap) - gap
    start_x = (CANVAS_WIDTH - total_w) // 2 # 水平居中起始点
    start_y = (CANVAS_HEIGHT - total_h) // 2 + 40 # 垂直居中起始点（向下偏移避开UI）

    # 定义背景黑色方块区域
    wall_rect = pygame.Rect(start_x - 35, start_y - 35, total_w + 70, total_h + 70)
    card_font = get_font(EMOJI_FONT, int(size * 0.7)) # 根据卡片大小调整图标大小

    card_list = []
    grid_slots = []
    # 嵌套循环生成网格坐标
    for i in range(rows):
        for j in range(cols):
            idx = i * cols + j # 线性索引
            x = start_x + j * (size + gap)
            y = start_y + i * (size + gap)
            # A. 记录背景格子的矩形，用于绘制底部的灰色空槽
            grid_slots.append(pygame.Rect(x, y, size, size))
            # B. 如果该索引还有卡片，则创建卡片对象
            if idx < len(cards_raw):
                card_list.append(Card(x, y, cards_raw[idx], size, icon_color_map[cards_raw[idx]], card_font))

    return card_list, grid_slots, wall_rect

# --- 5. 游戏主循环 (Game Loop) ---
screen = pygame.display.set_mode((CANVAS_WIDTH, CANVAS_HEIGHT))
pygame.display.set_caption("牛了个牛：三关终极修复版")

level_idx = 1
cards, slots, wall = create_level(level_idx) # 初始化第一关
selected = [] # 记录当前被选中的卡片列表
start_ticks = pygame.time.get_ticks() # 记录关卡开始时间
clock = pygame.time.Clock()
end_msg = "" # 存放通关或失败后的文字提示

running = True
while running:
    clock.tick(60) # 限制帧率为 60fps
    screen.fill(BG_COLOR) # 填充背景

    # A. 渲染背景层：绘制黑色挡板和灰色底槽
    pygame.draw.rect(screen, BLACK, wall, border_radius=20)
    for s in slots:
        pygame.draw.rect(screen, GRAY_SLOT, s, border_radius=8)

    # B. 渲染卡片层：遍历列表绘制所有未消除的卡片
    for c in cards:
        c.draw(screen)

    # C. 渲染顶层 UI：绘制顶部半透明遮罩条
    ui_surface = pygame.Surface((CANVAS_WIDTH, 80), pygame.SRCALPHA)
    pygame.draw.rect(ui_surface, (20, 20, 25, 180), (0, 0, CANVAS_WIDTH, 80))
    screen.blit(ui_surface, (0, 0))

    # 计算时间逻辑
    passed_sec = (pygame.time.get_ticks() - start_ticks) // 1000
    rem_sec = max(0, COUNTDOWN_TIME - passed_sec)

    # D. 渲染文字：关卡信息和倒计时
    level_txt = f"关卡: {level_idx} / 3"
    time_txt = f"剩余时间: {rem_sec // 60:02d}:{rem_sec % 60:02d}"
    font_ui.render_to(screen, (40, 25), level_txt, (255, 215, 0))
    font_ui.render_to(screen, (CANVAS_WIDTH - 320, 25), time_txt, WHITE)

    # E. 事件处理：监听退出和鼠标点击
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        if event.type == pygame.MOUSEBUTTONDOWN:
            # 检查点击了哪张卡片（反向遍历列表，优先检测上层卡片）
            for c in cards[:]:
                if c.is_clicked(event.pos):
                    if sound_click: sound_click.play()
                    if not c.selected and len(selected) < 3:
                        c.selected = True
                        selected.append(c) # 加入“选中区”
                    elif c.selected:
                        c.selected = False
                        selected.remove(c) # 如果点的是已选中的，则取消

            # 判定：如果选中了 3 张卡片
            if len(selected) == 3:
                # 如果三张图标一模一样
                if selected[0].icon == selected[1].icon == selected[2].icon:
                    if sound_match: sound_match.play()
                    for sc in selected:
                        if sc in cards: cards.remove(sc) # 消除！
                else:
                    # 如果不一样，所有选中的卡片闪烁后取消选中状态
                    for sc in selected: sc.selected = False
                selected = [] # 清空选中列表

    # F. 游戏状态逻辑检查
    if len(cards) == 0: # 如果该关卡卡片消完了
        if level_idx < 3:
            level_idx += 1
            cards, slots, wall = create_level(level_idx) # 进入下一关
            start_ticks = pygame.time.get_ticks() # 时间重置
        else:
            end_msg = "牛！你通关了全部三关！"
            running = False # 游戏胜利退出循环

    if rem_sec == 0: # 如果时间到了
        end_msg = "时间耗尽，再接再厉！"
        running = False # 游戏失败退出循环

    pygame.display.flip() # 刷新缓冲区，将画面显示到屏幕上

# --- 6. 结束展示阶段 ---
if end_msg:
    screen.fill(BG_COLOR)
    text_surf, rect = font_ui.render(end_msg, WHITE)
    rect.center = (CANVAS_WIDTH // 2, CANVAS_HEIGHT // 2)
    screen.blit(text_surf, rect)
    pygame.display.flip()
    pygame.time.wait(4000) # 停留 4 秒给玩家看结果

pygame.quit() # 彻底释放 Pygame 资源