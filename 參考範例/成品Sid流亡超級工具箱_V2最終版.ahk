; ★ Sid 流亡超級工具箱 - AHK v2 最終版 ★
; 編碼: UTF-8 with BOM
; 版本: AutoHotkey v2.0

; ======================================================================================================
; 程式初始化設定
; ======================================================================================================
#Requires AutoHotkey v2.0
#SingleInstance Force

; ======================================================================================================
; 引入模組
; ======================================================================================================
#Include AutoReplyGUIFunctions.ahk

; ======================================================================================================
; 配置管理系統
; ======================================================================================================

; 配置文件名稱
global CONFIG_FILE := "SidToolbox_V2_Config.ini"
global 當前狀態偵測GUI := ""



; ======================================================================================================
; 全域變數
; ======================================================================================================
使用者類型 := "免費用戶"
主選單 := ""
工具介紹子選單 := ""
工具暫停狀態 := false
; F9暫停前的狀態記錄
暫停前狀態 := Map(
    "StopUser", 0,
    "高級功能狀態", 0,
    "Autodrinkbutton", 0
)

; 首次使用標記
global 首次使用標記 := true
global 設置完成度 := 0

; 回復模式相關變數
回復模式 := "error"
自動回復內容 := "請稍等..."
StopUser := 0
Toolbutton := 0
openI := 0

; 循環技能相關變數
循環技能1 := "error"
循環技能2 := "error"
循環技能3 := "error"
循環技能4 := "error"
循環技能5 := "error"
循環技能時間1 := "error"
循環技能時間2 := "error"
循環技能時間3 := "error"
循環技能時間4 := "error"
循環技能時間5 := "error"

; 滑鼠監測相關變數
滑鼠開始時間 := 0

; 按鍵安全監控變數
ctrlPressed := false

; 清包控制變數
清包中斷標記 := false
清包進行中 := false

; 背包相關變數
清包模式 := "掃描式"
背包左上_X := "error"
背包左上_Y := "error"
背包右下_X := "error"
背包右下_Y := "error"
背包初始顏色1 := "error"
背包初始顏色2 := "error"

; 背包運算相關變數
背包每格寬 := 0
背包每格高 := 0
掃描開始左上_X := 0
掃描開始左上_Y := 0
掃描開始右下_X := 0
掃描開始右下_Y := 0
掃描水平數量 := 12
掃描垂直數量 := 5

; GUI變數
清包模式GUI := ""

; F1功能模式變數
F1原始鍵盤模式 := 0
F1功能模式 := 0
F1自訂序列 := "2-3-4-5-q"
F1按鍵間隔 := 50

; F2重複觸發變數
F2重複按鍵 := "space"
F2重複次數 := 5
F2重複間隔 := 100

; 快速交易功能變數
快速交易提醒 := "開啟"
快速組隊提醒 := "開啟"
對方背包左上_X := "error"
對方背包左上_Y := "error"
對方背包右下_X := "error"
對方背包右下_Y := "error"

; 自動引爆地雷系統變數
global 地雷功能狀態 := false
global 地雷按鍵設定 := Map()
global 位移地雷按鍵設定 := Map()
global 位移地雷延遲 := Map()
global 地雷GUI := ""
global 當前長按地雷按鍵 := ""

; 初始化地雷設定
地雷按鍵設定["Q"] := false
地雷按鍵設定["W"] := false
地雷按鍵設定["E"] := false
地雷按鍵設定["R"] := false
地雷按鍵設定["T"] := false

位移地雷按鍵設定["Q"] := false
位移地雷按鍵設定["W"] := false
位移地雷按鍵設定["E"] := false
位移地雷按鍵設定["R"] := false
位移地雷按鍵設定["T"] := false

位移地雷延遲["Q"] := 300
位移地雷延遲["W"] := 300
位移地雷延遲["E"] := 300
位移地雷延遲["R"] := 300
位移地雷延遲["T"] := 300

; F3循環變數
F3循環序列 := "q-w-e-r"
F3當前位置 := 1

; ToolTip 系統全域變數
global ToolTipSlots := Map()
global ToolTipTimers := Map()

; 座標定位GUI相關變數
global CoordInput := 0
global CoordGUI := ""

; 十字座標指示器相關變數
global CrosshairGUI := ""
global CrosshairActive := false
global CrosshairColor := "0xFF0000"
global CrosshairSize := 20
global CrosshairThickness := 3
global CrosshairTransparency := 200

; 智能MsgBox函數 - 處理GUI層級問題
SmartMsgBox(text, title, options := 0) {
    ; 記錄當前所有AlwaysOnTop GUI的狀態
    guiList := []
    
    ; 暫時關閉技能連段GUI
    try {
        if (IsObject(技能連段GUI) && WinExist("ahk_id " . 技能連段GUI.Hwnd)) {
            技能連段GUI.Opt("-AlwaysOnTop")
            guiList.Push(技能連段GUI)
        }
    }
    
    ; 檢查十字指示器GUI
    try {
        if (IsObject(CrosshairGUI) && WinExist("ahk_id " . CrosshairGUI.Hwnd)) {
            CrosshairGUI.Opt("-AlwaysOnTop")
            guiList.Push(CrosshairGUI)
        }
    }
    
    ; 顯示MsgBox
    result := MsgBox(text, title, options)
    
    ; 恢復所有GUI的AlwaysOnTop屬性
    for gui in guiList {
        try {
            if (IsObject(gui) && WinExist("ahk_id " . gui.Hwnd)) {
                gui.Opt("+AlwaysOnTop")
            }
        }
    }
    
    return result
}

; 血球魔力球偵測相關變數
偵測血球池打勾紀錄 := "-checked"
偵測魔球喝水打勾紀錄 := "-checked"
偵測血條喝水打勾紀錄 := "-checked"
偵測血條返角打勾紀錄 := "-checked"
偵測血條穿透打勾紀錄 := "-checked"
偵測穿透返角打勾紀錄 := "-checked"
藥劑按鍵2 := "error"
藥劑按鍵4 := "error"
狀態偵測間隔 := "500"
高級功能狀態 := 0

; 🔥 喝水冷卻管理系統 - 防止重複喝水
全域喝水冷卻 := Map()  ; 按鍵 -> 最後使用時間

; 計時器管理系統
計時器狀態 := Map(
    "血球偵測", false,
    "魔力球偵測", false,
    "場景偵測", false,
    "ES偵測", false,
    "血條偵測", false,
    "血條喝水偵測", false,
    "血條返角偵測", false,
    "血條穿透偵測", false,
    "穿透返角偵測", false
)

; 技能連段系統變數
global 技能連段狀態 := "關閉"
global 技能連段序列 := Map()
global 技能連段延遲 := Map()
global 技能連段GUI := ""

; 偵測間隔優化
偵測間隔設定 := Map(
    "血球偵測", 41,
    "魔力球偵測", 47,
    "場景偵測", 53,
    "ES偵測", 37,
    "血條偵測", 43,
    "血條喝水偵測", 61,
    "血條返角偵測", 67,
    "血條穿透偵測", 71,
    "穿透返角偵測", 73
)
偵測場景顏色 := "穩定"
ToolTipOff := 0

; GUI相關變數
血球魔力球設置GUI := ""
F1模式GUI := ""

; F6取物相關變數
通貨1X := 100, 通貨1Y := 100
通貨2X := 100, 通貨2Y := 100
通貨3X := 100, 通貨3Y := 100
通貨4X := 100, 通貨4Y := 100
通貨5X := 100, 通貨5Y := 100
F6取物延遲 := 20
F6取物模式 := 1

; F6智能連續座標設置相關變數
F6座標設置中 := false
F6當前設置編號 := 1
F6設置進度 := Map()

; 滑鼠連點相關變數
連點模式 := "滑鼠滾輪按壓"
滑鼠連點速度 := 25
clickStop := false

; 遊戲視窗檢測相關變數
遊戲視窗名稱 := ["Path of Exile", "Path of Exile 2", "PathOfExile_x64Steam.exe", "PathOfExile_Steam.exe", "PathOfExile_x64.exe", "PathOfExile.exe"]

; 快速查價相關變數
聲明顯示 := 0

; F7 座標設置相關變數
對方背包左上_X := "error"
對方背包左上_Y := "error"
對方背包右下_X := "error"
對方背包右下_Y := "error"
接受交易_X := "error"
接受交易_Y := "error"

; 取物功能相關變數
取物模式 := "error"
通貨1_X := "error"
通貨1_Y := "error"
通貨2_X := "error"

; 確保高級功能變數初始化
if (!IsSet(高級功能狀態)) {
    global 高級功能狀態 := 0
}
if (!IsSet(計時器狀態)) {
    global 計時器狀態 := Map(
        "血球偵測", false,
        "魔力球偵測", false,
        "場景偵測", false,
        "自訂偵測", false,
        "ES偵測", false,
        "血條偵測", false
    )
}
if (!IsSet(偵測間隔設定)) {
    global 偵測間隔設定 := Map(
        "血球偵測", 41,
        "魔力球偵測", 47,
        "場景偵測", 53,
        "自訂偵測", 59,
        "ES偵測", 37,
        "血條偵測", 43
    )
}
通貨2_Y := "error"
通貨3_X := "error"
通貨3_Y := "error"
通貨4_X := "error"
通貨4_Y := "error"
通貨5_X := "error"
通貨5_Y := "error"

; 文字偵測相關變數
Enter除錯提醒次數 := 0

; 顏色偵測相關變數
顏色1_X := "error"
顏色1_Y := "error"
顏色1_C := "error"
顏色2_X := "error"
顏色2_Y := "error"
顏色2_C := "error"
顏色3_X := "error"
顏色3_Y := "error"
顏色3_C := "error"
顏色4_X := "error"
顏色4_Y := "error"
顏色4_C := "error"
顏色5_X := "error"
顏色5_Y := "error"
顏色5_C := "error"
顏色6_X := "error"
顏色6_Y := "error"
顏色6_C := "error"
顏色7_X := "error"
顏色7_Y := "error"
顏色7_C := "error"
顏色8_X := "error"
顏色8_Y := "error"
顏色8_C := "error"
顏色9_X := "error"
顏色9_Y := "error"
顏色9_C := "error"

; 顏色偵測容錯設定
global 顏色容錯值 := 0

; ======================================================================================================
; 初始化系統
; ======================================================================================================
try {
    CoordMode("ToolTip", "Screen")
    ToolTip("步驟1: 系統初始化...", 10, 10, 1)
    系統初始化()
    
    ToolTip("步驟2: 建立選單...", 10, 10, 1)
    建立選單系統()
    
    ToolTip("步驟3: 註冊熱鍵...", 10, 10, 1)
    註冊熱鍵()
    
    ToolTip("步驟4: 顯示啟動訊息...", 10, 10, 1)
    顯示啟動訊息()
    
    ToolTip("✅ 系統啟動完成", 10, 10, 1)
    SetTimer(() => ToolTip("", 0, 0, 1), -3000)
    
} catch Error as err {
    MsgBox("啟動失敗於: " . err.Message . "`n錯誤行: " . err.Line . "`n錯誤文件: " . err.File, "系統錯誤", 0x10)
}

; ======================================================================================================
; 視窗檢測系統
; ======================================================================================================

; 檢查是否為流亡黯道遊戲視窗
檢查遊戲視窗() {
    global 遊戲視窗名稱
    
    try {
        ; 獲取當前活躍視窗的標題和進程名
        活躍視窗ID := WinGetID("A")
        視窗標題 := WinGetTitle("A")
        進程名 := WinGetProcessName("A")
        
        ; 檢查視窗標題或進程名是否包含遊戲相關關鍵字
        for 遊戲名 in 遊戲視窗名稱 {
            if (InStr(視窗標題, 遊戲名) || InStr(進程名, 遊戲名)) {
                return true
            }
        }
        
        return false
    } catch {
        return false
    }
}

; 帶視窗檢測的熱鍵包裝函數
安全執行熱鍵(功能函數) {
    global 工具暫停狀態
    if (工具暫停狀態) {
        return  ; 工具暫停中，不執行任何功能
    }
    if (檢查遊戲視窗()) {
        功能函數()
    }
}

; 高優先級執行熱鍵
高優先級執行熱鍵(功能函數) {
    global 工具暫停狀態
    if (工具暫停狀態) {
        return  ; 工具暫停中，不執行任何功能
    }
    if (檢查遊戲視窗()) {
        功能函數()
    }
}

; 智能座標設置熱鍵包裝函數
智能座標設置熱鍵(功能函數) {
    global 工具暫停狀態
    if (工具暫停狀態) {
        return  ; 工具暫停中，不執行任何功能
    }
    if (檢查座標GUI視窗()) {
        功能函數()
    }
    else if (檢查遊戲視窗()) {
        功能函數()
    }
    else {
        功能函數()
    }
}

; 檢查是否為座標設置GUI視窗
檢查座標GUI視窗() {
    try {
        視窗標題 := WinGetTitle("A")
        if (InStr(視窗標題, "🎯 座標定位工具") ||
            InStr(視窗標題, "🎯 F7背包定位工具") ||
            InStr(視窗標題, "Sid流亡工具箱")) {
            return true
        }
        return false
    } catch {
        return false
    }
}

; ======================================================================================================
; 首次使用引導系統
; ======================================================================================================

; 計算設置完成度
計算設置完成度() {
    global
    local 總項目數 := 0
    local 已完成數 := 0
    
    ; 步驟1：場景偵測點
    總項目數 += 1
    if (顏色1_X != "error" && 顏色1_Y != "error") {
        已完成數 += 1
    }
    
    ; 步驟2：對話框1偵測點
    總項目數 += 1
    if (顏色2_X != "error" && 顏色2_Y != "error") {
        已完成數 += 1
    }
    
    ; 步驟3：對話框2偵測點
    總項目數 += 1
    if (顏色3_X != "error" && 顏色3_Y != "error") {
        已完成數 += 1
    }
    
    ; 步驟4：個人背包座標
    總項目數 += 1
    if (背包左上_X != "error" && 背包左上_Y != "error" && 背包右下_X != "error" && 背包右下_Y != "error") {
        已完成數 += 1
    }
    
    ; 只計算快速設定精靈中的4個步驟，不包含回復模式和清包模式
    if (總項目數 > 0) {
        return Round((已完成數 / 總項目數) * 100)
    } else {
        return 0
    }
}

; 顯示首次使用引導
顯示首次使用引導() {
    global 首次使用標記, CONFIG_FILE
    
    歡迎訊息 := "🎉 歡迎使用 Sid 流亡超級工具箱！`n`n"
    歡迎訊息 .= "這是您第一次使用本工具，讓我為您快速設定核心功能：`n`n"
    歡迎訊息 .= "⚠️ 重要提醒：所有座標設定都需要【先將滑鼠移動到目標位置，再按熱鍵】`n`n"
    歡迎訊息 .= "📋 建議的初始設定步驟：`n"
    歡迎訊息 .= "1️ 場景偵測點：將滑鼠移到遊戲UI穩定區域 → 按 Win+C → 輸入 1`n"
    歡迎訊息 .= "2️ 對話框偵測點：將滑鼠移到對話框黑色區域 → 按 Win+C → 輸入 2、3`n"
    歡迎訊息 .= "3️ 個人背包座標：按 F7 → 依序點擊背包左上角和右下角`n"
    歡迎訊息 .= "4️ 清包設定：按 Win+F7 選擇清包方式和目標`n`n"
    歡迎訊息 .= "💡 提示：按 Win+Z 可以查看所有功能選單`n"
    歡迎訊息 .= "📖 詳細說明：可隨時在設定介面查看詳細操作說明`n`n"
    歡迎訊息 .= "現在要開啟快速設定精靈幫助您完成設定嗎？"
    
    result := MsgBox(歡迎訊息, "首次使用引導", 0x40 + 0x4)
    
    if (result == "Yes") {
        ; 標記已顯示過首次引導
        IniWrite("false", CONFIG_FILE, "系統設定", "首次使用標記")
        首次使用標記 := false
        
        ; 自動開啟設定介面
        SetTimer(() => 開啟快速設定精靈(), -500)
    } else {
        ; 即使使用者選擇No，也標記已顯示過引導
        IniWrite("false", CONFIG_FILE, "系統設定", "首次使用標記")
        首次使用標記 := false
    }
}

; 顯示設置提醒
顯示設置提醒() {
    global 設置完成度
    
    提醒訊息 := "⚠️ 檢測到您的設定可能不完整`n`n"
    提醒訊息 .= "目前設定完成度：" . 設置完成度 . "%`n`n"
    提醒訊息 .= "建議檢查以下設定：`n"
    
    if (顏色1_X = "error" || 顏色1_Y = "error") {
        提醒訊息 .= "• 場景偵測點 (Win+C → 代號 1)`n"
    }
    if (顏色2_X = "error" || 顏色2_Y = "error") {
        提醒訊息 .= "• 對話框1偵測點 (Win+C → 代號 2)`n"
    }
    if (顏色3_X = "error" || 顏色3_Y = "error") {
        提醒訊息 .= "• 對話框2偵測點 (Win+C → 代號 3)`n"
    }
    if (背包左上_X = "error" || 背包右下_X = "error") {
        提醒訊息 .= "• 個人背包座標 (F7 設定)`n"
    }
    
    提醒訊息 .= "`n是否要開啟設定精靈？"
    
    result := MsgBox(提醒訊息, "設定提醒", 0x30 + 0x4)
    
    if (result == "Yes") {
        開啟快速設定精靈()
    }
}

; 開啟快速設定精靈
開啟快速設定精靈() {
    設定精靈 := Gui("", "快速設定精靈")
    
    設定精靈.Add("Text", "x20 y20 w480 h35", "🎯 快速設定精靈 - 讓我們一步步完成設定").SetFont("s12 Bold")
    設定精靈.Add("Text", "x20 y65 w480 h25", "請按照以下步驟完成基本設定：").SetFont("s10")
    
    ; 步驟1：場景偵測點 (增加垂直間距)
    設定精靈.Add("Text", "x20 y100 w40 h25", "步驟1:").SetFont("s10 Bold")
    if (顏色1_X != "error" && 顏色1_Y != "error") {
        設定精靈.Add("Text", "x70 y100 w320 h25 cGreen", "✅ 場景偵測點已設定").SetFont("s10")
    } else {
        設定精靈.Add("Text", "x70 y100 w320 h25 cRed", "❌ 場景偵測點未設定").SetFont("s10")
        場景設定按鈕 := 設定精靈.Add("Button", "x400 y95 w90 h30", "立即設定")
        場景設定按鈕.OnEvent("Click", (*) => 設定場景偵測點())
        ; 添加場景偵測圖片指引按鈕
        if (FileExist("image/偵測場景變化設置.png")) {
            場景圖片按鈕 := 設定精靈.Add("Button", "x500 y95 w60 h30", "📷 圖例")
            場景圖片按鈕.OnEvent("Click", (*) => 顯示場景偵測設定圖片())
        }
    }
    
    ; 步驟2：對話框1偵測點 (Y座標增加40)
    設定精靈.Add("Text", "x20 y140 w40 h25", "步驟2:").SetFont("s10 Bold")
    if (顏色2_X != "error" && 顏色2_Y != "error") {
        設定精靈.Add("Text", "x70 y140 w320 h25 cGreen", "✅ 對話框1偵測點已設定").SetFont("s10")
    } else {
        設定精靈.Add("Text", "x70 y140 w320 h25 cRed", "❌ 對話框1偵測點未設定").SetFont("s10")
        對話框1設定按鈕 := 設定精靈.Add("Button", "x400 y135 w90 h30", "立即設定")
        對話框1設定按鈕.OnEvent("Click", (*) => 設定對話框1偵測點())
        ; 添加圖片指引按鈕
        if (FileExist("image/對話框設置.png")) {
            對話框1圖片按鈕 := 設定精靈.Add("Button", "x500 y135 w60 h30", "📷 圖例")
            對話框1圖片按鈕.OnEvent("Click", (*) => 顯示對話框設定圖片())
        }
    }
    
    ; 步驟3：對話框2偵測點 (Y座標增加40)
    設定精靈.Add("Text", "x20 y180 w40 h25", "步驟3:").SetFont("s10 Bold")
    if (顏色3_X != "error" && 顏色3_Y != "error") {
        設定精靈.Add("Text", "x70 y180 w320 h25 cGreen", "✅ 對話框2偵測點已設定").SetFont("s10")
    } else {
        設定精靈.Add("Text", "x70 y180 w320 h25 cRed", "❌ 對話框2偵測點未設定").SetFont("s10")
        對話框2設定按鈕 := 設定精靈.Add("Button", "x400 y175 w90 h30", "立即設定")
        對話框2設定按鈕.OnEvent("Click", (*) => 設定對話框2偵測點())
        ; 添加圖片指引按鈕
        if (FileExist("image/對話框設置.png")) {
            對話框2圖片按鈕 := 設定精靈.Add("Button", "x500 y175 w60 h30", "📷 圖例")
            對話框2圖片按鈕.OnEvent("Click", (*) => 顯示對話框設定圖片())
        }
    }
    
    ; 步驟4：背包座標 (Y座標增加40)
    設定精靈.Add("Text", "x20 y220 w40 h25", "步驟4:").SetFont("s10 Bold")
    if (背包左上_X != "error" && 背包右下_X != "error") {
        設定精靈.Add("Text", "x70 y220 w320 h25 cGreen", "✅ 個人背包座標已設定").SetFont("s10")
    } else {
        設定精靈.Add("Text", "x70 y220 w320 h25 cRed", "❌ 個人背包座標未設定").SetFont("s10")
        背包設定按鈕 := 設定精靈.Add("Button", "x400 y215 w90 h30", "立即設定")
        背包設定按鈕.OnEvent("Click", (*) => 設定背包座標())
        ; 添加背包設定圖片指引按鈕
        if (FileExist("image/F3圖例.png")) {
            背包圖片按鈕 := 設定精靈.Add("Button", "x500 y215 w60 h30", "📷 圖例")
            背包圖片按鈕.OnEvent("Click", (*) => 顯示背包設定圖片())
        }
    }
    
    ; 控制按鈕 (Y座標調整)
    設定精靈.Add("Button", "x80 y280 w90 h35", "重新檢查").OnEvent("Click", (*) => 重新檢查設定())
    設定精靈.Add("Button", "x190 y280 w90 h35", "完成設定").OnEvent("Click", (*) => 設定精靈.Destroy())
    設定精靈.Add("Button", "x300 y280 w90 h35", "詳細說明").OnEvent("Click", (*) => 顯示詳細說明())
    
    設定精靈.Show("w580 h340")
}

; 設定場景偵測點
設定場景偵測點() {
    開始座標設定引導("場景偵測點", "請將滑鼠移動到遊戲畫面中的場景變化偵測位置，然後按 Win+C 並輸入代號 1", 1)
}

; 設定對話框1偵測點
設定對話框1偵測點() {
    ; 直接開啟更完善的對話框設定指導GUI，而不是簡單的引導
    顯示對話框設定指導()
}

; 設定對話框2偵測點
設定對話框2偵測點() {
    ; 直接開啟更完善的對話框設定指導GUI，而不是簡單的引導
    顯示對話框設定指導()
}

; 設定背包座標
設定背包座標() {
    開始背包座標設定引導()
}

; 設定回復模式
設定回復模式() {
    ShowInfo("正在開啟偵測喝水設置面板...", 2000)
    ; 觸發偵測喝水設置面板
    Send("#z")
}

; ======================================================================================================
; 🎯 座標設定引導系統
; ======================================================================================================

; 全域變數追蹤引導狀態
設定引導模式 := false
當前設定精靈GUI := ""
當前引導說明 := ""

; 開始座標設定引導
開始座標設定引導(名稱, 說明文字, 代號) {
    global 設定引導模式, 當前設定精靈GUI, 當前引導說明
    
    ; 隱藏所有可能的GUI視窗
    try {
        ; 嘗試關閉任何打開的設定精靈視窗
        WinClose("快速設定精靈")
    } catch {
        ; 忽略關閉錯誤
    }
    
    ; 嘗試活躍遊戲視窗
    try {
        if (WinExist("Path of Exile")) {
            WinActivate("Path of Exile")
        } else if (WinExist("Path of Exile 2")) {
            WinActivate("Path of Exile 2")
        }
        Sleep(500)  ; 等待視窗切換
    } catch {
        ; 忽略視窗切換錯誤
    }
    
    ; 啟動引導模式
    設定引導模式 := true
    
    ; 設置引導Tooltip內容
    當前引導說明 := "🎯 " . 名稱 . " 設定引導`n`n" . 說明文字 . "`n`n⚠️ 按 Esc 可取消並返回設定精靈"
    
    ; 設置引導Tooltip
    SetTimer(更新引導Tooltip, 100)  ; 更頻繁更新以確保跟隨
    
    ; 綁定Esc鍵取消引導
    Hotkey("Escape", 取消座標設定引導, "On")
    
    ; 顯示初始引導訊息
    MouseGetPos(&mx, &my)
    ToolTip(當前引導說明, mx + 20, my - 60)
}

; 開始背包座標設定引導
開始背包座標設定引導() {
    global 設定引導模式, 當前設定精靈GUI, 當前引導說明
    
    ; 隱藏所有可能的GUI視窗
    try {
        ; 嘗試關閉任何打開的設定精靈視窗
        WinClose("快速設定精靈")
    } catch {
        ; 忽略關閉錯誤
    }
    
    ; 嘗試活躍遊戲視窗
    try {
        if (WinExist("Path of Exile")) {
            WinActivate("Path of Exile")
        } else if (WinExist("Path of Exile 2")) {
            WinActivate("Path of Exile 2")
        }
        Sleep(500)  ; 等待視窗切換
    } catch {
        ; 忽略視窗切換錯誤
    }
    
    ; 啟動引導模式
    設定引導模式 := true
    
    ; 設置引導Tooltip內容
    當前引導說明 := "🎯 背包座標設定引導`n`n請按 F7 開始設定背包座標`n代號 1-5 對應不同的座標點`n1:背包左上 2:背包右下 3:對方背包左上 4:對方背包右下 5:接受交易`n`n⚠️ 按 Esc 可取消並返回設定精靈"
    
    ; 設置引導Tooltip
    SetTimer(更新背包引導Tooltip, 100)  ; 更頻繁更新以確保跟隨
    
    ; 綁定Esc鍵取消引導
    Hotkey("Escape", 取消座標設定引導, "On")
    
    ; 顯示背包設定圖片引導
    顯示背包設定圖片()
    
    ; 顯示初始引導訊息
    MouseGetPos(&mx, &my)
    ToolTip(當前引導說明, mx + 20, my - 80)
}

; 更新引導Tooltip (跟隨滑鼠)
更新引導Tooltip() {
    global 當前引導說明
    if (!設定引導模式) {
        SetTimer(更新引導Tooltip, 0)
        return
    }
    
    MouseGetPos(&mx, &my)
    ; 重新設置Tooltip位置到滑鼠右側，避免遮擋
    if (IsSet(當前引導說明) && 當前引導說明 != "") {
        ToolTip(當前引導說明, mx + 20, my - 60)
    }
}

; 更新背包引導Tooltip (跟隨滑鼠)
更新背包引導Tooltip() {
    global 當前引導說明
    if (!設定引導模式) {
        SetTimer(更新背包引導Tooltip, 0)
        return
    }
    
    MouseGetPos(&mx, &my)
    ; 重新設置Tooltip位置到滑鼠右側，避免遮擋
    if (IsSet(當前引導說明) && 當前引導說明 != "") {
        ToolTip(當前引導說明, mx + 20, my - 60)
    }
}

; 取消座標設定引導
取消座標設定引導(*) {
    global 設定引導模式, 當前設定精靈GUI
    
    if (!設定引導模式) {
        return
    }
    
    ; 停止引導模式
    設定引導模式 := false
    
    ; 停止計時器
    SetTimer(更新引導Tooltip, 0)
    SetTimer(更新背包引導Tooltip, 0)
    
    ; 清除Tooltip
    ToolTip()
    
    ; 解除Esc鍵綁定
    try {
        Hotkey("Escape", 取消座標設定引導, "Off")
    } catch {
        ; 忽略解除綁定錯誤
    }
    
    ; 關閉所有可能的圖片視窗
    try {
        WinClose("背包座標設定圖例")
    } catch {
        ; 忽略關閉錯誤
    }
    
    ; 重新顯示設定精靈 - 但要避免重複開啟
    Sleep(200)  ; 短暫延遲確保所有GUI已關閉
    try {
        ; 先確保沒有重複的快速設定精靈視窗
        WinClose("快速設定精靈")
        Sleep(100)
        開啟快速設定精靈()
    } catch {
        ; 如果出現錯誤，重新開啟設定精靈
        開啟快速設定精靈()
    }
    
    ShowToolTip("✅ 已返回快速設定精靈", 2000, 1)
}

; 引導完成返回精靈
引導完成返回精靈(*) {
    ; 直接取消引導模式，不重複開啟精靈
    global 設定引導模式
    
    if (!設定引導模式) {
        return
    }
    
    ; 停止引導模式
    設定引導模式 := false
    
    ; 停止計時器
    SetTimer(更新引導Tooltip, 0)
    SetTimer(更新背包引導Tooltip, 0)
    
    ; 清除Tooltip
    ToolTip()
    
    ; 解除Esc鍵綁定
    try {
        Hotkey("Escape", 取消座標設定引導, "Off")
    } catch {
        ; 忽略解除綁定錯誤
    }
    
    ; 關閉所有可能的圖片視窗
    try {
        WinClose("背包座標設定圖例")
    } catch {
        ; 忽略關閉錯誤
    }
    
    ; 延遲後開啟設定精靈，避免重複
    Sleep(300)
    try {
        ; 先確保沒有重複的快速設定精靈視窗
        WinClose("快速設定精靈")
        Sleep(100)
        開啟快速設定精靈()
        ShowToolTip("✅ 座標設定完成，已返回快速設定精靈", 2000, 1)
    } catch {
        ; 忽略錯誤，確保引導模式正常結束
        ShowToolTip("✅ 座標設定完成", 2000, 1)
    }
}

; 重新檢查設定
重新檢查設定() {
    global 設置完成度
    設置完成度 := 計算設置完成度()
    ShowInfo("設定檢查完成，目前完成度：" . 設置完成度 . "%", 3000)
}

; 顯示詳細說明
顯示詳細說明() {
    說明內容 := "📖 詳細設定說明`n`n"
    說明內容 .= "⚠️ 重要操作順序：`n"
    說明內容 .= "所有座標設定都需要【先將滑鼠移動到目標位置，再按熱鍵】`n`n"
    說明內容 .= "場景偵測點 (代號1)：`n"
    說明內容 .= "• 用於判斷當前是否在遊戲中`n"
    說明內容 .= "• 設定方法：先將滑鼠移動到遊戲下方UI介面顏色穩定之區域 → 按 Win+C → 輸入 1`n`n"
    說明內容 .= "對話框1偵測點 (代號2)：`n"
    說明內容 .= "• 用於偵測Enter對話框是否出現`n"
    說明內容 .= "• 設定方法：先將滑鼠移動到對話框黑色區域 → 按 Win+C → 輸入 2`n`n"
    說明內容 .= "對話框2偵測點 (代號3)：`n"
    說明內容 .= "• 用於偵測位移對話框是否出現`n"
    說明內容 .= "• 設定方法：先將滑鼠移動到對話框黑色區域 → 按 Win+C → 輸入 3`n`n"
    說明內容 .= "個人背包座標：`n"
    說明內容 .= "• 用於清包和取物功能`n"
    說明內容 .= "• 設定方法：按 F7 → 先將滑鼠移動到背包左上角位置 → 再將滑鼠移動到右下角位置`n`n"
    說明內容 .= "💡 操作要點：`n"
    說明內容 .= "• 滑鼠位置決定抓取的座標點`n"
    說明內容 .= "• 確保滑鼠指向正確位置再按熱鍵`n"
    說明內容 .= "• 熱鍵是用來確認當前滑鼠位置的座標`n"
    
    MsgBox(說明內容, "詳細設定說明", 0x40)
}

; ======================================================================================================
; 函數定義
; ======================================================================================================

; 系統初始化
系統初始化() {
    global 使用者類型, 回復模式, 自動回復內容, 清包模式
    global 連點模式, 滑鼠連點速度, 首次使用標記, 設置完成度
    
    ; 暫時跳過 ConfigManager 初始化
    ; ConfigManager.Initialize()
    
    try {
        ; 讀取用戶授權狀態
        高級鑰匙 := RegRead("HKEY_LOCAL_MACHINE\SOFTWARE\SGAMEAPP\tool", "passkey", "")
        if (高級鑰匙 = "open") {
            使用者類型 := "已贊助"
        }
        
        ; 讀取首次使用標記
        首次使用標記 := IniRead(CONFIG_FILE, "系統設定", "首次使用標記", "true")
        if (首次使用標記 = "true") {
            首次使用標記 := true
        } else {
            首次使用標記 := false
        }
        
        ; 讀取配置檔案
        F1讀取值 := IniRead(CONFIG_FILE, "按鍵模式切換", "F1原始鍵盤模式", "0")
        F1原始鍵盤模式 := (F1讀取值 = "1") ? 1 : 0
        
        if (F1原始鍵盤模式 != 0 && F1原始鍵盤模式 != 1) {
            F1原始鍵盤模式 := 0
            IniWrite(F1原始鍵盤模式, CONFIG_FILE, "按鍵模式切換", "F1原始鍵盤模式")
        }
        
        模式顯示 := (F1原始鍵盤模式 = 1) ? "原始鍵盤模式" : "返角模式"
        ShowInfo("F1模式已載入: " . 模式顯示 . " (讀取值: '" . F1讀取值 . "' → " . F1原始鍵盤模式 . ")", 5000)
        
        回復模式 := IniRead(CONFIG_FILE, "按鍵模式切換", "回復模式", "error")
        自動回復內容 := IniRead(CONFIG_FILE, "自動回復設定", "自動回復內容", "請稍等...")
        清包模式 := IniRead(CONFIG_FILE, "按鍵模式切換", "清包模式", "一鍵清包")
        取物模式 := IniRead(CONFIG_FILE, "按鍵模式切換", "取物模式", "error")
        
        連點模式 := IniRead(CONFIG_FILE, "按鍵模式切換", "連點模式", "滑鼠滾輪按壓")
        滑鼠連點速度 := IniRead(CONFIG_FILE, "按鍵模式切換", "滑鼠連點速度", "25")
        
        讀取循環技能設置()
        載入技能連段設定()
        載入地雷設定()
        
        讀取F7背包定位內容()
        背包運算作業()
        
        讀取F6取物定位內容()
        
        背包初始顏色1 := IniRead(CONFIG_FILE, "快速掃描顏色", "背包初始顏色1", "error")
        背包初始顏色2 := IniRead(CONFIG_FILE, "快速掃描顏色", "背包初始顏色2", "error")
        
        讀取顏色座標()
        
        Enter除錯提醒次數 := IniRead(CONFIG_FILE, "系統設定", "Enter除錯提醒次數", "0")
        
        更新全域偵測變數()
        
        try {
            global 高級功能狀態 := 0
            global Autodrinkbutton := 0
            
            SetTimer(() => ShowF10Status("F10偵測功能已就緒 (預設關閉，按F10啟動)", 3000), -1000)
            
        } catch {
            global 高級功能狀態 := 0
        }
        
        設置完成度 := 計算設置完成度()
        
        ; 移除自動首次使用引導，改為在啟動精靈中觸發
        ; 如果設置不完整時顯示提醒
        if (設置完成度 < 50 && !首次使用標記) {
            SetTimer(() => 顯示設置提醒(), -3000)
        }
        
    } catch Error as err {
        ; V2錯誤處理
        MsgBox("初始化錯誤: " . err.Message, "系統錯誤", 0x10)
    }
}

; 建立選單系統
建立選單系統() {
    global 工具介紹子選單, 主選單
    
    ; 工具介紹子選單
    工具介紹子選單 := Menu()
    工具介紹子選單.Add("📋 工具熱鍵列表", 工具熱鍵列表說明)
    工具介紹子選單.Add("🆓 完整功能介紹", 功能說明)

    ; 主選單
    主選單 := Menu()
    主選單.Add("⭐ 工具介紹 ⭐ (必看)", 工具介紹子選單)
    主選單.Add()  ; 分隔線
    主選單.Add("🚀 重新開啟快速設定精靈", (*) => 開啟快速設定精靈())
    主選單.Add()  ; 分隔線
    主選單.Add("💚 狀態偵測設置", 狀態設置說明)
    主選單.Add("⚔️ 技能連段設置", 技能設置說明)
    主選單.Add("🔄 循環技能設置", 循環設置說明)
    主選單.Add()  ; 分隔線
    主選單.Add("🎯 智能拾取設置 (F8)", F8_智能拾取設置)
    主選單.Add("💱 快速交易熱鍵", 快速交易設置說明)
    主選單.Add()  ; 分隔線
    主選單.Add("🖱️ 滑鼠連點設置", 連點設置說明)
    主選單.Add("💣 自動引爆地雷設置", 地雷設置說明)
    主選單.Add("💰 前往查價工具的網址", 開啟查價網站)
    主選單.Add()  ; 分隔線
    主選單.Add("🌐 前往 Sid 作者網站", 開啟作者網站)
}

; 註冊熱鍵
註冊熱鍵() {
    ; 系統管理熱鍵
    HotKey("F11", (*) => Reload())
    HotKey("F12", 結束程式)
    HotKey("^+F12", (*) => 強制釋放按鍵())
    HotKey("#k", 複製硬碟序號)
    
    ; 遊戲功能熱鍵
    HotKey("~*Esc", (*) => 安全執行熱鍵(處理ESC鍵))
    HotKey("F9", 暫停工具)  ; F9 不通過安全執行熱鍵包裝，確保暫停時也能工作
    HotKey("#z", (*) => 安全執行熱鍵(顯示主選單))
    
    ; 座標設置熱鍵
    HotKey("#c", (*) => 智能座標設置熱鍵(座標定位功能))
    HotKey("F7", (*) => 智能座標設置熱鍵(F7_座標設置))
    
    ; 文字模式偵測熱鍵
    HotKey("~*Enter", (*) => 安全執行熱鍵(Enter偵測對話框))
    HotKey("~*^f", (*) => 安全執行熱鍵(Ctrl_F偵測))
    
    ; 背包狀態監測熱鍵
    HotKey("~*i", (*) => 安全執行熱鍵(監測背包狀態))
    
    ; 滑鼠左鍵監測熱鍵
    HotKey("~*LButton", (*) => 安全執行熱鍵(監測滑鼠左鍵))
    
    HotKey("F1", (*) => 安全執行熱鍵(F1_功能))
    HotKey("#F1", (*) => 安全執行熱鍵(F1_選單))
    HotKey("F2", (*) => 安全執行熱鍵(F2_回復模式))
    HotKey("#F2", (*) => 安全執行熱鍵(F2_選單))
    HotKey("F3", (*) => 高優先級執行熱鍵(F3_功能))
    HotKey("#F3", (*) => 安全執行熱鍵(Win_F3_功能))
    HotKey("F4", (*) => ShowToolTip("功能待開發!", 3000, 1))
    HotKey("#F4", (*) => ShowToolTip("F4 功能待開發!", 3000, 1))
    HotKey("F5", (*) => 安全執行熱鍵(F5_返回藏身))
    HotKey("#F5", (*) => 安全執行熱鍵(F5_說明))
    HotKey("F6", (*) => 安全執行熱鍵(F6_一鍵取物))
    HotKey("#F6", (*) => 安全執行熱鍵(F6_選單))
    HotKey("#F7", (*) => 安全執行熱鍵(F7_說明))
    
    ; Win+V 特殊處理
    HotKey("#v", Win_V_智能切換)
    
    ; 循環技能相關熱鍵
    HotKey("Insert", (*) => 安全執行熱鍵(Insert_循環技能))
    HotKey("#x", (*) => 高優先級執行熱鍵(Show_MouseClickGui))
    
    ; 快速交易熱鍵
    HotKey("End", (*) => 安全執行熱鍵(End_快速組隊))
    HotKey("Home", (*) => 安全執行熱鍵(Home_快速交易))
    HotKey("PgUp", (*) => 安全執行熱鍵(PgUp_確認交易欄位))
    HotKey("PgDn", (*) => 安全執行熱鍵(PgDn_接受交易))
}

; ========================== 統一ToolTip管理系統 ==========================

; 統一的ToolTip顯示函數
; ======================================================================================================
; 🎯 統一ToolTip管理系統 - 重新設計版本
; ======================================================================================================

; 🔧 ToolTip優先級分配表：
; Priority 1: 🚨 錯誤和警告訊息 (最高優先級，紅色區域)
; Priority 2: F10偵測系統和模式切換 (綠色區域)
; Priority 3: 即時狀態更新 (藍色區域)
; Priority 4: 一般提示和操作回饋 (黃色區域)
; Priority 5: 進度和統計資訊 (灰色區域)

; 推薦的調用方式：
; ShowError("錯誤訊息")     - 用於錯誤、失敗、異常
; ShowF10Status("狀態")    - 用於F10系統的模式切換
; ShowStatus("狀態更新")    - 用於即時狀態變化  
; ShowInfo("一般提示")      - 用於操作回饋和說明 (預設)
; ShowProgress("進度")      - 用於處理進度和統計

ShowToolTip(message, duration := 3000, priority := 4) {
    global ToolTipSlots, ToolTipTimers
    
    ; 確保優先級在1-5範圍內
    if (priority < 1) priority := 1
    if (priority > 5) priority := 5
    
    ; 🔥 清除該槽位的舊計時器
    if (ToolTipTimers.Has(priority)) {
        try {
            SetTimer(ToolTipTimers[priority], 0)
        } catch {
        }
    }
    
    ; 設置座標模式為螢幕模式
    CoordMode("ToolTip", "Screen")
    
    ; 根據優先級設置不同的顯示位置和顏色主題
    switch priority {
        case 1:  ; 錯誤警告 - 螢幕右上角，醒目位置
            x := A_ScreenWidth - 350
            y := 10
        case 2:  ; F10系統 - 螢幕左上角，固定位置
            x := 10  
            y := 10
        case 3:  ; 即時狀態 - 螢幕左上角，次要位置
            x := 10
            y := 40
        case 4:  ; 💡 一般提示 - 螢幕左上角，標準位置
            x := 10
            y := 70
        case 5:  ; 📊 進度統計 - 螢幕左上角，底部位置
            x := 10
            y := 100
    }
    
    ; 顯示ToolTip
    ToolTip(message, x, y, priority)
    ToolTipSlots[priority] := message
    
    ; 設置自動清除計時器
    if (duration > 0) {
        ToolTipTimers[priority] := () => ClearToolTip(priority)
        SetTimer(ToolTipTimers[priority], -duration)
    }
}

; 清除指定槽位的ToolTip
ClearToolTip(slot) {
    global ToolTipSlots, ToolTipTimers
    
    CoordMode("ToolTip", "Screen")
    ToolTip("", 0, 0, slot)
    if (ToolTipSlots.Has(slot)) {
        ToolTipSlots.Delete(slot)
    }
    if (ToolTipTimers.Has(slot)) {
        ToolTipTimers.Delete(slot)
    }
}

; 🔥 統一的文字模式提示函數 (重構優化)
顯示文字模式提示() {
    ShowToolTip("您現在是文字模式，請嘗試點擊一小段路 或 Enter", 3000, 1)
}

; 清除所有ToolTip
ClearAllToolTips() {
    global ToolTipSlots, ToolTipTimers
    
    CoordMode("ToolTip", "Screen")
    Loop 5 {
        ToolTip("", 0, 0, A_Index)
        try {
            if (ToolTipTimers.Has(A_Index)) {
                SetTimer(ToolTipTimers[A_Index], 0)
            }
        } catch {
        }
    }
    ToolTipSlots.Clear()
    ToolTipTimers.Clear()
}

; 🎯 分類ToolTip函數 - 提供更直觀的調用方式

; 錯誤和警告訊息 (Priority 1)
ShowError(message, duration := 4000) {
    ShowToolTip("🚨 " . message, duration, 1)
}

; F10系統和模式切換 (Priority 2)  
ShowF10Status(message, duration := 2500) {
    ShowToolTip(message, duration, 2)
}

; 即時狀態更新 (Priority 3)
ShowStatus(message, duration := 1500) {
    ShowToolTip("⚡ " . message, duration, 3)
}

; 一般提示和操作回饋 (Priority 4) - 預設
ShowInfo(message, duration := 3000) {
    ShowToolTip("💡 " . message, duration, 4)
}

; 進度和統計資訊 (Priority 5)
ShowProgress(message, duration := 1000) {
    ShowToolTip("📊 " . message, duration, 5)
}

; 相容性函數 - 替代原有的ToolTipShow
ToolTipShow(label) {
    ShowInfo(label, 3000)  ; 使用一般提示級別
    try {
        if (WinExist("Path of Exile 2")) {
            WinActivate("Path of Exile 2")
        } else {
            WinActivate("Path of Exile")
        }
    } catch {
    }
}

GetDriveTailSerial() {
    try {
        for objItem in ComObjGet("winmgmts:\\.\root\cimv2").ExecQuery("Select * from Win32_PhysicalMedia") {
            serial := objItem.SerialNumber
            if (serial != "" && !InStr(serial, "00000000")) {
                clean := RegExReplace(serial, "[^a-zA-Z0-9]")
                if (StrLen(clean) >= 12)
                    return SubStr(clean, -11)
                else
                    return clean
            }
        }
    } catch {
        return "UNKNOWN"
    }
    return "UNKNOWN"
}

; 熱鍵處理函數
暫停工具(*) {
    global 工具暫停狀態, 暫停前狀態, StopUser, 高級功能狀態, Autodrinkbutton
    
    if (工具暫停狀態) {
        ; 恢復工具 - 使用現有的開關系統恢復狀態
        工具暫停狀態 := false
        
        ; 重新啟用所有熱鍵
        try {
            HotKey("#z", (*) => 安全執行熱鍵(顯示主選單), "On")
            HotKey("#v", Win_V_智能切換, "On")
            HotKey("~*Esc", (*) => 安全執行熱鍵(處理ESC鍵), "On")
            HotKey("#k", 複製硬碟序號, "On")
            HotKey("#c", (*) => 智能座標設置熱鍵(座標定位功能), "On")
            HotKey("F7", (*) => 智能座標設置熱鍵(F7_座標設置), "On")
            HotKey("~*Enter", (*) => 安全執行熱鍵(Enter偵測對話框), "On")
            HotKey("~*^f", (*) => 安全執行熱鍵(Ctrl_F偵測), "On")
            HotKey("~*i", (*) => 安全執行熱鍵(監測背包狀態), "On")
            HotKey("~*LButton", (*) => 安全執行熱鍵(監測滑鼠左鍵), "On")
            HotKey("F1", (*) => 安全執行熱鍵(F1_功能), "On")
            HotKey("#F1", (*) => 安全執行熱鍵(F1_選單), "On")
            HotKey("F2", (*) => 安全執行熱鍵(F2_回復模式), "On")
            HotKey("#F2", (*) => 安全執行熱鍵(F2_選單), "On")
            HotKey("F3", (*) => 高優先級執行熱鍵(F3_功能), "On")
            HotKey("#F3", (*) => 安全執行熱鍵(Win_F3_功能), "On")
            HotKey("F4", (*) => ShowToolTip("功能待開發!", 3000, 1), "On")
            HotKey("#F4", (*) => ShowToolTip("F4 功能待開發!", 3000, 1), "On")
            HotKey("F5", (*) => 安全執行熱鍵(F5_返回藏身), "On")
            HotKey("#F5", (*) => 安全執行熱鍵(F5_說明), "On")
            HotKey("F6", (*) => 安全執行熱鍵(F6_一鍵取物), "On")
            HotKey("#F6", (*) => 安全執行熱鍵(F6_選單), "On")
            HotKey("#F7", (*) => 安全執行熱鍵(F7_說明), "On")
            HotKey("Insert", (*) => 安全執行熱鍵(Insert_循環技能), "On")
            HotKey("#x", (*) => 高優先級執行熱鍵(Show_MouseClickGui), "On")
            HotKey("End", (*) => 安全執行熱鍵(End_快速組隊), "On")
            HotKey("Home", (*) => 安全執行熱鍵(Home_快速交易), "On")
            HotKey("PgUp", (*) => 安全執行熱鍵(PgUp_確認交易欄位), "On")
            HotKey("PgDn", (*) => 安全執行熱鍵(PgDn_接受交易), "On")
        }
        
        ; 恢復各功能的狀態 - 使用現有的開關系統
        try {
            ; 恢復循環技能狀態
            if (暫停前狀態["StopUser"] = 1) {
                StopUser := 1
                啟動循環技能()
            }
            
            ; 恢復高級功能狀態
            if (暫停前狀態["高級功能狀態"] >= 1) {
                高級功能狀態 := 暫停前狀態["高級功能狀態"]
                Autodrinkbutton := 暫停前狀態["Autodrinkbutton"]
                if (高級功能狀態 == 1) {
                    啟動基礎偵測()
                } else if (高級功能狀態 == 2) {
                    啟動完整偵測()
                }
            }
        }
        
        ToolTipShow("工具已恢復運作！所有功能已恢復到暫停前狀態。")
    } else {
        ; 暫停工具 - 記錄當前狀態並使用現有的關閉系統
        工具暫停狀態 := true
        
        ; 記錄當前狀態
        暫停前狀態["StopUser"] := StopUser
        暫停前狀態["高級功能狀態"] := 高級功能狀態
        暫停前狀態["Autodrinkbutton"] := Autodrinkbutton
        
        ; 停用所有熱鍵（保留F9、F11、F12、Ctrl+Shift+F12）
        try {
            HotKey("#z", "Off")
            HotKey("#v", "Off")
            HotKey("~*Esc", "Off")
            HotKey("#k", "Off")
            HotKey("#c", "Off")
            HotKey("F7", "Off")
            HotKey("~*Enter", "Off")
            HotKey("~*^f", "Off")
            HotKey("~*i", "Off")
            HotKey("~*LButton", "Off")
            HotKey("F1", "Off")
            HotKey("#F1", "Off")
            HotKey("F2", "Off")
            HotKey("#F2", "Off")
            HotKey("F3", "Off")
            HotKey("#F3", "Off")
            HotKey("F4", "Off")
            HotKey("#F4", "Off")
            HotKey("F5", "Off")
            HotKey("#F5", "Off")
            HotKey("F6", "Off")
            HotKey("#F6", "Off")
            HotKey("#F7", "Off")
            HotKey("Insert", "Off")
            HotKey("#x", "Off")
            HotKey("End", "Off")
            HotKey("Home", "Off")
            HotKey("PgUp", "Off")
            HotKey("PgDn", "Off")
        }
        
        ; 使用現有的關閉系統停止所有功能
        try {
            ; 關閉循環技能
            if (StopUser = 1) {
                關閉循環技能()
                StopUser := 0
            }
            
            ; 關閉所有偵測功能
            if (高級功能狀態 >= 1) {
                停止所有偵測()
                高級功能狀態 := 0
                Autodrinkbutton := 0
            }
        }
        
        ToolTipShow("工具暫停中，回復原始鍵盤功能，[F9]恢復運作。")
    }
}

結束程式(*) {
    MsgBox("工具已結束 ლ(・ω・ლ)摸摸", "提示", 0)
    ExitApp()
}

處理ESC鍵(*) {
    ; 重置一些變數狀態
    global openI := 0
    global Toolbutton := 0
    global 滑鼠開始時間 := 0
    global ctrlPressed := false
    
    ; 關閉滑鼠彈起監聽器（如果有的話）
    try {
        HotKey("~*LButton Up", "Off")
    }
    
    ; 🔧 強制釋放可能卡住的按鍵狀態
    強制釋放按鍵()
    
    ; 如果在遊戲視窗中，顯示提示
    if (檢查遊戲視窗()) {
        ToolTipShow("(ESC) 關閉面板，返回遊戲模式")
    }
}

複製硬碟序號(*) {
    serialTail := GetDriveTailSerial()
    A_Clipboard := serialTail
    MsgBox("需提供給作者的實體硬碟序號尾碼已複製到剪貼簿：`n`n" . serialTail, "硬碟序號已複製", 0x40)
}

顯示主選單(*) {
    global 主選單
    ; 只在Path of Exile視窗中顯示選單
    if (WinActive("Path of Exile") || WinActive("Path of Exile 2"))
        主選單.Show()
    else
        主選單.Show()  ; 或者可以顯示，但提醒用戶
}

; Win+V 智能切換功能
Win_V_智能切換(*) {
    global 工具暫停狀態
    if (工具暫停狀態) {
        ; 工具暫停中，直接使用系統原生 Win+V 功能
        Send("#v")
        return
    }
    if (檢查遊戲視窗()) {
        ; 在遊戲視窗中執行快速查價
        快速查價()
    } else {
        ; 不在遊戲視窗時，恢復系統 Win+V 功能（剪貼板歷史）
        Send("#v")
    }
}

快速查價(*) {
    ; 激活查價工具視窗
    查價工具視窗()
}

; 查價工具視窗功能
查價工具視窗() {
    global 聲明顯示
    
    ; 檢查是否存在 rchin-poe-trade 視窗
    if WinExist("rchin-poe-trade") {
        ; 如果查價工具視窗存在，直接執行查價操作
        ShowToolTip("Sid工具支援查價時 [ Esc ] 快速返回 POE 視窗", 3000, 1)
        
        ; 複製選中內容
        Send("^c")
        
        ; 激活查價工具
        try {
            WinActivate("rchin-poe-trade")
        }
        return
    }
    
    ; 獲取當前滑鼠位置
    thisPosX := 0
    thisPosY := 0
    MouseGetPos(&thisPosX, &thisPosY)
    
    if (聲明顯示 == 0) {
        MsgBox("請記得安裝並預先開啟【rchin-poe-trade】工具，並點擊 Home 返回遊戲，Win + V 才可正常運作。`r`r如未安裝，您可在 Win + Z 菜單中找到*前往查價工具的網址*的欄位`r`r申明:此查價工具並非Sid製作，也未對此功能進行任何收費。`r`r僅抱持著推廣與分享目的提供使用，請多支持原創作者。", "每次開起工具僅顯示一次，關閉後請再次使用 Win + V 即可。", "T3 64")
        聲明顯示 := 1
        
        ; 激活POE視窗
        try {
            if (WinExist("Path of Exile 2")) {
                WinActivate("Path of Exile 2")
            } else {
                WinActivate("Path of Exile")
            }
        }
        return
    }
    
    if (聲明顯示 == 1) {
        ShowToolTip("Sid工具支援查價時 [ Esc ] 快速返回 POE 視窗", 3000, 1)
        
        ; 複製選中內容
        Send("^c")
        
        ; 激活查價工具
        try {
            WinActivate("rchin-poe-trade")
        }
    }
}

; ========================== 通用設定管理函數 ==========================

; 即時讀取INI設定
即時讀取設定(區段, 鍵值, 預設值 := "") {
    ; 使用固定配置檔案
    configFile := CONFIG_FILE
    return IniRead(configFile, 區段, 鍵值, 預設值)
}

; 即時寫入INI設定並確認
即時寫入設定(區段, 鍵值, 數值) {
    configFile := CONFIG_FILE  ; 使用固定配置檔案
    try {
        IniWrite(數值, configFile, 區段, 鍵值)
        ; 讀取確認寫入成功
        確認值 := IniRead(configFile, 區段, 鍵值, "")
        return (確認值 = String(數值))
    } catch {
        return false
    }
}

; ========================== 功能熱鍵函數 ==========================

; F1 返回角色功能
F1_功能(*) {
    global F1原始鍵盤模式
    
    F1讀取值 := 即時讀取設定("按鍵模式切換", "F1原始鍵盤模式", "0")
    F1原始鍵盤模式 := (F1讀取值 = "1") ? 1 : 0
    
    if (Toolbutton = 1) {
        顯示文字模式提示()
        return
    }
    
    if (F1原始鍵盤模式 = 0) {
        返角()
    }
    else if (F1原始鍵盤模式 = 1) {
        try {
            HotKey("F1", "Off")
            Send("{F1}")
            Sleep(100)
            HotKey("F1", (*) => 安全執行熱鍵(F1_功能))
        } catch Error as err {
            try {
                HotKey("F1", (*) => 安全執行熱鍵(F1_功能))
            } catch {
            }
            ShowError("原始鍵盤模式執行失敗: " . err.Message, 3000)
        }
    }
    else {
        ; 如果值不正確，重設為返角模式，立即寫入
        if (即時寫入設定("按鍵模式切換", "F1原始鍵盤模式", 0)) {
            F1原始鍵盤模式 := 0
            ShowError("F1模式異常，已自動重設為返角模式，請再按一次F1", 3000)
        } else {
            ShowError("F1模式重設失敗，請檢查INI文件", 3000)
        }
    }
}

; Win + F1 選單
F1_選單(*) {
    global
    Show_F1ModeGui()
}

; 返回角色功能
返角() {
    global
    
    ; 暫停循環喝水 (如果有相關函數)
    try {
        if (IsSet(停止所有偵測)) {
            停止所有偵測()
        }
    } catch {
        ; 忽略錯誤，繼續執行
    }
    
    try {
        BlockInput(true)
        Send("{Enter}")
        Sleep(25)
        A_Clipboard := "/exit"
        Send("^v")
        Sleep(25)
        Send("{Enter}")
        BlockInput(false)
        
        ; 倒數提示
        ShowToolTip("3秒後自動Enter登入", 1000, 1)
        Sleep(1000)
        ShowToolTip("2秒後自動Enter登入", 1000, 1)
        Sleep(1000)
        ShowToolTip("1秒後自動Enter登入", 1000, 1)
        Sleep(1000)
        ShowToolTip("0秒後自動Enter登入", 1000, 1)
        Send("{Enter}")
        
        ShowToolTip("", 0, 1)  ; 清除ToolTip
        
    } catch Error as err {
        ShowError("返角失敗: " . err.Message, 3000)
    } finally {
        BlockInput(false)
    }
}

; F1 模式選擇GUI
Show_F1ModeGui() {
    global F1模式GUI
    
    try {
        if (IsObject(F1模式GUI)) {
            F1模式GUI.Destroy()
        }
        
        F1模式GUI := Gui("+Resize -MinimizeBox -MaximizeBox +AlwaysOnTop", "🎮 F1按鍵模式設定")
        F1模式GUI.BackColor := "0xF0F8FF"
        F1模式GUI.MarginX := 15
        F1模式GUI.MarginY := 10
        
        F1模式GUI.SetFont("s12 Bold", "Microsoft JhengHei")
        F1模式GUI.Add("Text", "w290 Center c0x000080", "請選擇 F1 按鍵功能模式")
        F1模式GUI.Add("Text", "w290 h1 0x10")
        
        ; 當前模式狀態顯示
        當前模式 := (F1原始鍵盤模式 = 1) ? "原始鍵盤模式" : "返角模式"
        F1模式GUI.SetFont("s10", "Microsoft JhengHei")
        F1模式GUI.Add("Text", "w290 Center c0x008000", "目前模式：" . 當前模式)
        
        ; 添加小間距
        F1模式GUI.Add("Text", "w290 h2")  ; 極小間距
        
        ; 添加按鈕 - 調整尺寸適合320px寬度
        F1模式GUI.SetFont("s11 Bold", "Microsoft JhengHei")
        F1模式GUI.Add("Button", "w290 h32 c0x0000FF", "🔄 回復原始鍵盤").OnEvent("Click", (*) => 設定F1模式(1))
        F1模式GUI.Add("Text", "w290 h2")  ; 極小按鈕間距
        F1模式GUI.Add("Button", "w290 h32 c0xFF0000", "⚡ 激活返角熱鍵").OnEvent("Click", (*) => 設定F1模式(0))
        
        ; 添加說明文字
        F1模式GUI.Add("Text", "w290 h2")  ; 極小間距
        F1模式GUI.SetFont("s9", "Microsoft JhengHei")
        F1模式GUI.Add("Text", "w290 Center c0x808080", "提示：選擇後設定將自動儲存")
        
        ; 計算螢幕置中位置並顯示
        螢幕寬度 := A_ScreenWidth
        螢幕高度 := A_ScreenHeight
        GUI寬度 := 320
        GUI高度 := 220  ; 移除StatusBar後減少高度
        置中X := (螢幕寬度 - GUI寬度) // 2
        置中Y := (螢幕高度 - GUI高度) // 2
        F1模式GUI.Show("w" . GUI寬度 . " h" . GUI高度 . " x" . 置中X . " y" . 置中Y)
        
    } catch Error as err {
        ShowError("創建F1模式選擇GUI時發生錯誤: " . err.message, 5000)
    }
}

; 設定F1模式
設定F1模式(新模式值) {
    global F1原始鍵盤模式, F1模式GUI
    
    try {
        ; 立即寫入新模式到INI
        if (即時寫入設定("按鍵模式切換", "F1原始鍵盤模式", 新模式值)) {
            F1原始鍵盤模式 := 新模式值
            模式名稱 := (F1原始鍵盤模式 = 1) ? "原始鍵盤模式" : "返角模式"
            ShowInfo("✅ F1按鍵已變更為: " . 模式名稱 . " (即時生效)", 3000)
        } else {
            ShowError("F1模式設定失敗，請重試", 3000)
        }
        
        ; 關閉GUI
        if (IsObject(F1模式GUI)) {
            F1模式GUI.Destroy()
        }
        
    } catch Error as err {
        ShowError("設定F1模式時發生錯誤: " . err.message, 3000)
    }
}

; F2 回復模式
F2_回復模式(*) {
    global
    
    ; 每次使用熱鍵時重新讀取INI設定
    回復模式 := 即時讀取設定("按鍵模式切換", "回復模式", "error")
    
    if (Toolbutton = 1) {
        顯示文字模式提示()
        return
    }
    
    if (回復模式 = "error") {
        ShowToolTip("第一次使用F2的朋友你好！`n試試 Win + F2 進行選擇吧！", 5000, 1)
        return
    }
    
    if (回復模式 = "暫離") {
        if (StopUser = 0) {  ; 如果循環技能關閉
            Set_AFK()
        }
        if (StopUser = 1) {  ; 如果循環技能開啟
            StopUser := 0
            ; 關閉循環技能邏輯
            ShowToolTip("已關閉[Ins]技能循環，進入暫離狀態。", 3000, 2)
            Set_AFK()
        }
    }
    
    if (回復模式 = "勿擾")
        Set_DND()
        
    if (回復模式 = "自動回復") {
        if (自動回復內容 = "error") {
            ; 設定自動回復功能
            return
        }
        else {
            Set_AutoReply()
        }
    }
}

; ========================== F3 清包功能 ==========================

; F3 清包功能
F3_功能(*) {
    global
    if (Toolbutton = 1) {
        顯示文字模式提示()
        return
    }
    
    ; 檢查是否設定了背包位置
    if (背包左上_X = "error" or 背包右下_X = "error") {
        ShowToolTip("尚未設定背包位置，請打開背包使用F7設定。", 3000, 1)
        try {
            顯示F3設定指導()
        }
        return
    }
    
    ; 檢查背包顏色定位狀態
    最新背包初始顏色1 := IniRead(CONFIG_FILE, "快速掃描顏色", "背包初始顏色1", "error")
    最新背包初始顏色2 := IniRead(CONFIG_FILE, "快速掃描顏色", "背包初始顏色2", "error")
    
    顏色定位已完成 := false
    ; 檢查是否有任何背包顏色資料
    if (最新背包初始顏色1 != "error" && 最新背包初始顏色2 != "error") {
        顏色定位已完成 := true
    }
    
    if (!顏色定位已完成) {
        ; 如果當前是"變更顏色定位"模式，直接執行顏色定位
        if (清包模式 = "變更顏色定位") {
            ShowToolTip("🎯 開始背包顏色定位，請確保背包已打開且為空", 3000, 1)
            快速掃描背包顏色並儲存()
            return
        } else {
            ; 如果不是顏色定位模式，建議切換模式
            ShowToolTip("⚠️ 尚未進行背包顏色定位`n💡 請按 Win+F3 切換為「背包顏色定位」模式", 4000, 1)
            return
        }
    }
    
    switch 清包模式 {
        case "掃描式":
            if (使用者類型 = "已贊助") {
                智能掃描並存倉()
            } else {
                ShowToolTip("清包功能正在執行中，請稍候。", 3000, 1)
            }
            
        case "變更顏色定位":
            快速掃描背包顏色並儲存()
    }
}

; Win+F3 選單
Win_F3_功能(*) {
    F3_選單()
}

; F3 選單
F3_選單() {
    global
    
    if (!IsSet(清包模式GUI)) {
        Show_ClearBagModeGui()
    } else {
        try {
            清包模式GUI.Show()
        } catch {
            Show_ClearBagModeGui()
        }
    }
}

; 智能掃描並存倉 - 修正版，立即處理避免漏點
智能掃描並存倉() {
    global 背包左上_X, 背包左上_Y, 背包每格寬, 背包每格高
    global 掃描開始左上_X, 掃描開始左上_Y, 掃描水平數量, 掃描垂直數量
    global 清包中斷標記, 清包進行中
    
    try {
        ; 檢查背包座標是否已設定
        if (背包左上_X = "error" or 背包每格寬 = 0) {
            ShowToolTip("尚未設定背包位置，請打開背包使用F7設定", 3000, 1)
            return
        }
        
        ; 初始化清包狀態
        清包中斷標記 := false
        清包進行中 := true
        
        ShowToolTip("開始智能掃描清包... (長按滑鼠右鍵可中斷)", 2000, 1)
        
        ; 安全的Ctrl操作：設置標記變數
        global ctrlPressed := true
        
        ; 按住Ctrl鍵進行掃描和存倉
        Send("{Ctrl down}")
        處理數量 := 0
        迴圈狀態 := 0
        
        ; 智能掃描：按列從左到右掃描，立即處理發現的物品
        Loop 掃描水平數量 {  ; 12列
            ; 每列開始前檢查是否需要中斷
            if (清包中斷標記 || !ctrlPressed || !WinActive("Path of Exile") && !WinActive("Path of Exile 2")) {
                ShowToolTip("🛑 清包已中斷於第 " . A_Index . " 列", 2000, 1)
                break
            }
            
            當前列 := A_Index
            ; 計算X座標 (使用原版公式)
            PosX := (掃描開始左上_X + (背包每格寬/2)) + ((背包每格寬/2) * ((當前列-1) * 2))
            
            列有物品 := false
            
            Loop 掃描垂直數量 {  ; 5行
                ; 每格檢查中斷標記
                if (清包中斷標記 || GetKeyState("RButton", "P")) {
                    if (GetKeyState("RButton", "P")) {
                        清包中斷標記 := true
                        ShowToolTip("🛑 偵測到滑鼠右鍵，清包已中斷", 2000, 1)
                    } else {
                        ShowToolTip("🛑 清包已中斷於第 " . 當前列 . " 列第 " . A_Index . " 行", 2000, 1)
                    }
                    break 2  ; 跳出兩層迴圈
                }
                
                當前行 := A_Index
                迴圈狀態++
                
                ; 計算Y座標 (使用原版公式)
                PosY := (掃描開始左上_Y + (背包每格高/2)) + ((背包每格高/2) * ((當前行-1) * 2))
                
                ; 檢查該位置是否有物品
                當前顏色 := PixelGetColor(PosX, PosY)
                
                ; 讀取對應位置的背包初始顏色
                預期顏色 := IniRead(CONFIG_FILE, "快速掃描顏色", "背包初始顏色" . 迴圈狀態, "0x040404")
                
                ; 如果當前顏色不等於預期的背包初始顏色，立即處理
                if (當前顏色 != 預期顏色) {
                    ; 移動滑鼠到物品位置
                    MouseMove(PosX, PosY, 0)
                    Sleep(10)
                    
                    ; 🔥 同時點擊右鍵和左鍵進行清包（提高效率）
                    Click(PosX, PosY, "Right", 1)
                    Sleep(5)  ; 短暫延遲
                    Click(PosX, PosY, "Left", 1)
                    Sleep(15)
                    
                    ; 驗證是否成功存倉
                    新顏色 := PixelGetColor(PosX, PosY)
                    if (新顏色 = 預期顏色) {
                        處理數量++
                        列有物品 := true
                    } else {
                        ; 如果第一次沒成功，再試一次（同樣使用雙擊）
                        Sleep(10)
                        Click(PosX, PosY, "Right", 1)
                        Sleep(5)
                        Click(PosX, PosY, "Left", 1)
                        Sleep(15)
                        
                        ; 再次驗證
                        新顏色2 := PixelGetColor(PosX, PosY)
                        if (新顏色2 = 預期顏色) {
                            處理數量++
                            列有物品 := true
                        }
                    }
                }
                
                ; 短暫停頓，避免過快掃描
                Sleep(5)
            }
            
            ; 如果這列有處理物品，顯示進度
            if (列有物品) {
                ShowProgress("正在處理第 " . 當前列 . " 列，已處理 " . 處理數量 . " 個物品", 300)
            }
        }
        
        ; 安全釋放Ctrl鍵
        ctrlPressed := false
        Send("{Ctrl up}")  ; 釋放Ctrl鍵
        
        ; 🔥 重置清包狀態
        清包進行中 := false
        
        ; 顯示完成結果
        if (清包中斷標記) {
            ShowToolTip("⏹️ 清包已被右鍵中斷，共處理了 " . 處理數量 . " 個物品", 2500, 1)
        } else if (處理數量 > 0) {
            ShowToolTip("✅ 智能掃描完成，成功處理了 " . 處理數量 . " 個物品", 2000, 1)
        } else {
            ShowToolTip("✅ 掃描完成：背包已清空", 1500, 1)
        }
        
    } catch Error as e {
        ; 🔧 異常處理：確保釋放Ctrl鍵
        ctrlPressed := false
        清包進行中 := false
        Send("{Ctrl up}")  ; 確保釋放Ctrl鍵
        強制釋放按鍵()  ; 額外的安全措施
        ShowToolTip("智能掃描出錯：" . e.Message, 3000, 1)
    } finally {
        ; 🔥 最終確保重置狀態
        清包進行中 := false
        清包中斷標記 := false
    }
}

; 快速掃描背包顏色並儲存
快速掃描背包顏色並儲存() {
    global 背包左上_X, 背包左上_Y, 背包每格寬, 背包每格高, 掃描水平數量, 掃描垂直數量
    global 掃描開始左上_X, 掃描開始左上_Y
    
    ; 掃描並儲存背包的完整60格顏色資料
    try {
        if (背包左上_X = "error" or 背包每格寬 = 0) {
            ShowToolTip("請先使用 F7 設定背包左上角和右下角座標！", 3000, 1)
            return
        }
        
        ; 初始化掃描參數（12列x5行=60格）
        掃描水平數量 := 12
        掃描垂直數量 := 5
        掃描開始左上_X := Integer(背包左上_X)
        掃描開始左上_Y := Integer(背包左上_Y)
        
        迴圈狀態 := 0
        掃描顏色Array := []
        
        ShowToolTip("開始掃描背包60格顏色...", 2000, 1)  ; 2秒後自動清除
        
        ; 按列掃描（12列，每列5格）
        Loop 掃描水平數量 {
            當前列 := A_Index
            PosX := (掃描開始左上_X + (背包每格寬/2)) + ((背包每格寬/2) * ((當前列-1) * 2))
            
            Loop 掃描垂直數量 {
                當前行 := A_Index
                PosY := (掃描開始左上_Y + (背包每格高/2)) + ((背包每格高/2) * ((當前行-1) * 2))
                
                ; 滑鼠移動到當前掃描位置（快速移動）
                MouseMove(PosX, PosY, 0)
                
                ; 獲取顏色
                pcol := PixelGetColor(PosX, PosY)
                掃描顏色Array.Push(pcol)
                迴圈狀態 := 迴圈狀態 + 1
                
                ; 顯示掃描狀態
                ShowProgress("掃描進度: " . 迴圈狀態 . "/60 - 顏色: " . pcol, 0)
                
                ; 儲存每個格子的顏色
                IniWrite(pcol, CONFIG_FILE, "快速掃描顏色", "背包初始顏色" . 迴圈狀態)
                
                ; 快速掃描延遲
                Sleep(20)
            }
        }
        
        ; 清除進度提示
        ClearAllToolTips()
        
        ; 更新 global 變數，讓系統知道顏色定位已完成
        global 背包初始顏色1, 背包初始顏色2
        背包初始顏色1 := IniRead(CONFIG_FILE, "快速掃描顏色", "背包初始顏色1", "error")
        背包初始顏色2 := IniRead(CONFIG_FILE, "快速掃描顏色", "背包初始顏色2", "error")
        
        ; 完成提示並自動切換回智能掃描模式
        ShowToolTip("掃描並儲存完畢！已記錄" . 迴圈狀態 . "格顏色資料", 2000, 1)
        
        ; 自動切換回智能掃描模式
        自動切換到智能掃描模式()
        
    } catch Error as err {
        ClearAllToolTips()
        ShowToolTip("背包顏色掃描失敗: " . err.Message, 3000, 1)
    }
}

; 自動切換到智能掃描模式
自動切換到智能掃描模式() {
    global 清包模式
    
    ; 更新清包模式
    清包模式 := "掃描式"
    
    ; 保存到配置檔案
    IniWrite(清包模式, CONFIG_FILE, "按鍵模式切換", "清包模式")
    
    ; 顯示切換提示
    ShowToolTip("已自動切換至智能掃描模式！`n現在可以直接使用 F3 進行智能清包。", 3000, 1)
}

; 清包模式選擇GUI
Show_ClearBagModeGui() {
    global 清包模式GUI  ; 使其成為全域變數
    
    清包模式GUI := Gui("+AlwaysOnTop -MinimizeBox -MaximizeBox", "🎒 F3清包模式設定")
    清包模式GUI.BackColor := "0xF5F5F5"  ; 淺灰色背景
    清包模式GUI.MarginX := 15
    清包模式GUI.MarginY := 10
    
    ; 設置標題
    清包模式GUI.SetFont("s12 Bold", "Microsoft JhengHei")
    清包模式GUI.Add("Text", "w290 Center c0x000080", "請選擇背包清理模式")
    清包模式GUI.Add("Text", "w290 h1 0x10")  ; 更細分隔線
    
    ; 當前模式狀態
    清包模式GUI.SetFont("s10", "Microsoft JhengHei")
    清包模式GUI.Add("Text", "w290 Center c0x008000", "目前模式：" . 清包模式)
    
    ; 添加小間距
    
    ; 功能按鈕
    清包模式GUI.SetFont("s11 Bold", "Microsoft JhengHei")
    清包模式GUI.Add("Button", "w290 h32 c0x0000FF", "🔍 智能掃描清包").OnEvent("Click", (*) => 變更清包模式("掃描式"))
    清包模式GUI.Add("Text", "w290 h2")  ; 極小按鈕間距
    清包模式GUI.Add("Button", "w290 h32 c0x800080", "🎯 背包顏色定位").OnEvent("Click", (*) => 變更清包模式("變更顏色定位"))
    
    ; 添加說明
    清包模式GUI.Add("Text", "w290 h2")  ; 極小間距
    清包模式GUI.SetFont("s9", "Microsoft JhengHei")
    清包模式GUI.Add("Text", "w290 Center c0x808080", "提示：智能掃描適合快速清理")
    
    ; 計算螢幕置中位置並顯示
    螢幕寬度 := A_ScreenWidth
    螢幕高度 := A_ScreenHeight
    GUI寬度 := 320
    GUI高度 := 210  ; 增加10px高度改善底部空間
    置中X := (螢幕寬度 - GUI寬度) // 2
    置中Y := (螢幕高度 - GUI高度) // 2
    清包模式GUI.Show("w" . GUI寬度 . " h" . GUI高度 . " x" . 置中X . " y" . 置中Y)
}

變更清包模式(模式) {
    global 清包模式, 清包模式GUI
    
    ; 移除贊助版檢查，完全免費使用
    清包模式 := 模式
    try {
        IniWrite(清包模式, CONFIG_FILE, "按鍵模式切換", "清包模式")
    }
    
    ; 關閉GUI
    if (IsSet(清包模式GUI)) {
        清包模式GUI.Destroy()
    }
    
    if (模式 = "變更顏色定位") {
        ShowToolTip("你正切換為顏色定位模式，請在[F7]背包座標確實抓取後再使用此模式，`n開啟[I]並保持背包淨空，使用[F3]讓工具掃描顏色紀錄數據。", 5000, 1)
    } else {
        ShowToolTip("已切換到: " . 模式, 2000, 2)
    }
}

; F2 選單
F2_選單(*) {
    Show_ReplyModeGui()
}

; 回復模式相關函數
Set_AFK() {
    try {
        BlockInput(true)
        Send("{Enter}")
        Sleep(25)
        A_Clipboard := "/afk"
        Send("^v")
        Sleep(25)
        Send("{Enter}")
    } catch Error as err {
        ShowToolTip("暫離設定失敗: " . err.Message, 3000, 1)
    } finally {
        BlockInput(false)
    }
}

Set_DND() {
    try {
        BlockInput(true)
        Send("{Enter}")
        Sleep(25)
        A_Clipboard := "/dnd"
        Send("^v")
        Sleep(25)
        Send("{Enter}")
    } catch Error as err {
        ShowToolTip("勿擾設定失敗: " . err.Message, 3000, 1)
    } finally {
        BlockInput(false)
    }
}

Set_AutoReply() {
    global 自動回復內容
    
    try {
        BlockInput(true)
        Send("{Enter}")
        Sleep(25)
        A_Clipboard := "/autoreply " . 自動回復內容
        Send("^v")
        Sleep(25)
        Send("{Enter}")
    } catch Error as err {
        ShowToolTip("自動回復設定失敗: " . err.Message, 3000, 1)
    } finally {
        BlockInput(false)
    }
}

; 回復模式選擇GUI
Show_ReplyModeGui() {
    global 回復模式GUI  ; 使其成為全域變數
    
    回復模式GUI := Gui("+AlwaysOnTop -MinimizeBox -MaximizeBox", "💬 F2回復模式設定")
    回復模式GUI.BackColor := "0xFFF8DC"  ; 淺黃色背景
    回復模式GUI.MarginX := 15
    回復模式GUI.MarginY := 10
    
    ; 設置標題
    回復模式GUI.SetFont("s12 Bold", "Microsoft JhengHei")
    回復模式GUI.Add("Text", "w290 Center c0x000080", "請選擇聊天回復模式")
    回復模式GUI.Add("Text", "w290 h1 0x10")  ; 更細分隔線
    
    ; 當前模式狀態
    回復模式GUI.SetFont("s10", "Microsoft JhengHei")
    回復模式GUI.Add("Text", "w290 Center c0x008000", "目前模式：" . 回復模式)
    
    ; 添加小間距 - 減少2px靠近模式顯示
    ; 回復模式GUI.Add("Text", "w290 h2")  ; 移除此間距讓按鈕更靠近
    
    ; 基本功能按鈕 - 更新文字提示會立即執行
    回復模式GUI.SetFont("s11 Bold", "Microsoft JhengHei")
    回復模式GUI.Add("Button", "w290 h32 c0x0000FF", "⏸️ 暫離模式 (立即執行)").OnEvent("Click", (*) => 變更回復模式("暫離"))
    回復模式GUI.Add("Text", "w290 h2")  ; 極小按鈕間距
    回復模式GUI.Add("Button", "w290 h32 c0xFF0000", "🔕 勿擾模式 (立即執行)").OnEvent("Click", (*) => 變更回復模式("勿擾"))
    
    回復模式GUI.Add("Text", "w290 h2")  ; 極小按鈕間距
    回復模式GUI.Add("Button", "w290 h32 c0x008000", "🤖 自動回復 (立即執行)").OnEvent("Click", (*) => 變更回復模式("自動回復"))
    回復模式GUI.Add("Text", "w290 h2")  ; 極小按鈕間距
    回復模式GUI.Add("Button", "w290 h32 c0x800080", "⚙️ 設定自動回復內容").OnEvent("Click", (*) => 設定自動回復內容())
    
    ; 添加說明
    回復模式GUI.Add("Text", "w290 h2")  ; 極小間距
    回復模式GUI.SetFont("s9", "Microsoft JhengHei")
    回復模式GUI.Add("Text", "w290 Center c0x808080", "提示：選擇後會自動激活遊戲並執行功能")
    
    ; 計算螢幕置中位置並顯示
    螢幕寬度 := A_ScreenWidth
    螢幕高度 := A_ScreenHeight
    GUI寬度 := 320
    GUI高度 := 350  ; 增加10px高度改善底部空間
    置中X := (螢幕寬度 - GUI寬度) // 2
    置中Y := (螢幕高度 - GUI高度) // 2
    回復模式GUI.Show("w" . GUI寬度 . " h" . GUI高度 . " x" . 置中X . " y" . 置中Y)
}

變更回復模式(模式) {
    global 回復模式, 回復模式GUI, 遊戲視窗名稱
    回復模式 := 模式
    try {
        IniWrite(回復模式, CONFIG_FILE, "按鍵模式切換", "回復模式")
        
        ; 重新讀取確認設定成功
        回復模式 := IniRead(CONFIG_FILE, "按鍵模式切換", "回復模式", "error")
    }
    
    ; 關閉GUI
    if (IsSet(回復模式GUI)) {
        回復模式GUI.Destroy()
    }
    
    ShowToolTip("已切換到: " . 模式 . " 並立即執行", 2000, 2)
    
    ; 🎯 激活遊戲視窗並立即執行對應功能
    try {
        ; 嘗試激活流亡黯道遊戲視窗
        for 視窗名稱 in 遊戲視窗名稱 {
            if WinExist(視窗名稱) {
                WinActivate(視窗名稱)
                Sleep(100)  ; 等待視窗激活
                break
            }
        }
        
        ; 立即執行對應的回復模式功能
        switch 模式 {
            case "暫離":
                Set_AFK()
            case "勿擾":
                Set_DND()
            case "自動回復":
                Set_AutoReply()
        }
        
    } catch Error as err {
        ShowToolTip("執行回復模式時發生錯誤: " . err.Message, 3000, 1)
    }
}

設定自動回復內容() {
    global 自動回復內容, 回復模式GUI
    
    ; 關閉GUI
    if (IsSet(回復模式GUI)) {
        回復模式GUI.Destroy()
    }
    
    ; 創建現代化自動回復設定GUI
    CreateAutoReplyGui()
}

; ========================== F5 返回藏身功能 ==========================

; F5 返回藏身
F5_返回藏身(*) {
    global
    if (Toolbutton = 1) {
        ToolTip("您現在是文字模式，請嘗試點擊一小段路 或 Enter")
        return
    }
    
    返回藏身()
}

; Win + F5 說明
F5_說明(*) {
    ToolTip("本工具的 [Win + F5] 沒有多功能切換哦~ ^0^")
    SetTimer(() => ToolTip(), -3000)
}

; 返回藏身功能
返回藏身() {
    try {
        BlockInput(true)
        Send("{Enter}")
        Sleep(25)
        A_Clipboard := "/hideout"
        Send("^v")
        Sleep(25)
        Send("{Enter}")
    } catch Error as err {
        ShowToolTip("返回藏身失敗: " . err.Message, 3000, 1)
    } finally {
        BlockInput(false)
    }
}

; ========================== F6 一鍵取物功能 ==========================

; F6 一鍵取物
F6_一鍵取物(*) {
    global 通貨1X, 通貨1Y, 通貨2X, 通貨2Y, 通貨3X, 通貨3Y, 通貨4X, 通貨4Y, 通貨5X, 通貨5Y
    global F6取物延遲, F6取物模式
    
    ; 首次使用F6功能提示
    static 首次F6使用 := true
    if (首次F6使用) {
        首次F6使用 := false
        ShowInfo("🎉 歡迎使用F6一鍵取物功能！`n請先使用 Win+F6 設定取物座標", 4000)
    }
    
    ; 檢查座標是否已設置
    ; 注意：只在所有通貨座標都未設定時才視為未設定（之前使用 OR 會在任一座標未設定時誤判）
    if (通貨1X <= 100 && 通貨2X <= 100 && 通貨3X <= 100 && 通貨4X <= 100 && 通貨5X <= 100) {
        ShowError("尚未設置取物座標！`n請先使用 Win+F6 設定取物座標位置")
        return
    }
    
    ; 如果模式為 1，使用快速一鍵取物（改為點擊已設定的 5 個座標）
    if (F6取物模式 = 1) {
    ; 重新讀取座標以確保使用最新值
    讀取F6取物定位內容()

    ; 調試顯示：顯示當前模式與座標
    dbg := "F6模式:" . F6取物模式 . "\n"
    dbg .= "1:(" . 通貨1X . "," . 通貨1Y . ")  "
    dbg .= "2:(" . 通貨2X . "," . 通貨2Y . ")  "
    dbg .= "3:(" . 通貨3X . "," . 通貨3Y . ")\n"
    dbg .= "4:(" . 通貨4X . "," . 通貨4Y . ")  "
    dbg .= "5:(" . 通貨5X . "," . 通貨5Y . ")\n"
    dbg .= "config:" . CONFIG_FILE
    ToolTip(dbg)
    SetTimer(() => ToolTip(), -1800)

        BlockInput(true)
        try {
            ; 構建座標陣列
            通貨座標 := [[通貨1X, 通貨1Y], [通貨2X, 通貨2Y], [通貨3X, 通貨3Y], [通貨4X, 通貨4Y], [通貨5X, 通貨5Y]]

            for 座標 in 通貨座標 {
                ; 如果遊戲視窗不在前景，停止
                if (!WinActive("Path of Exile") && !WinActive("Path of Exile 2")) {
                    break
                }

                currX := 座標[1]
                currY := 座標[2]

                ; 只有在座標有效時才移動並點擊
                if (currX > 100 && currY > 100) {
                    MouseMove(currX, currY, 0)
                    Sleep(F6取物延遲)

                    ; 使用安全的 Ctrl 處理進行點擊
                    Send("{Ctrl down}")
                    Click()
                    Send("{Ctrl up}")
                    Sleep(F6取物延遲)
                }
            }
        } catch Error as e {
            ; 確保釋放 Ctrl
            Send("{Ctrl up}")
            ShowToolTip("F6取物異常：" . e.Message, 2000, 1)
        } finally {
            Send("{Ctrl up}")
            BlockInput(false)
        }
        ToolTip("快速一鍵取物完成")
        SetTimer(() => ToolTip(), -1500)
    }
    ; 如果模式為 2，使用取物座標定位（原始版F6行為）
    else if (F6取物模式 = 2) {
        ; 檢查是否有座標資料，如果沒有就彈出設置視窗
        if (通貨1X <= 100 && 通貨2X <= 100 && 通貨3X <= 100 && 通貨4X <= 100 && 通貨5X <= 100) {
            F6快速取物定位()  ; 彈出座標設置視窗
        } else {
            ; 執行座標定位取物
            BlockInput(true)
            try {
                ; 安全的座標定位模式
                通貨座標 := [[通貨1X, 通貨1Y], [通貨2X, 通貨2Y], [通貨3X, 通貨3Y], [通貨4X, 通貨4Y], [通貨5X, 通貨5Y]]
                
                for 座標 in 通貨座標 {
                    ; 檢查是否仍在遊戲視窗中
                    if (!WinActive("Path of Exile") && !WinActive("Path of Exile 2")) {
                        break
                    }
                    
                    currX := 座標[1]
                    currY := 座標[2]
                    
                    if (currX > 100 && currY > 100) {
                        MouseMove(currX, currY, 0)
                        Sleep(F6取物延遲)
                        
                        ; 安全的Ctrl處理
                        Send("{Ctrl down}")
                        Click()
                        Send("{Ctrl up}")
                        Sleep(F6取物延遲)
                    }
                }
            } catch Error as e {
                ; 🔧 異常處理：確保釋放Ctrl
                Send("{Ctrl up}")
                ShowToolTip("座標取物異常：" . e.Message, 2000, 1)
            } finally {
                ; 🔧 最終保證：釋放所有修飾鍵
                Send("{Ctrl up}")
                BlockInput(false)
            }
            ToolTip("座標取物完成")
            SetTimer(() => ToolTip(), -1500)
        }
    }
}

; F6快速取物定位（原始版F6座標設置功能）
F6快速取物定位() {
    global
    
    ; 獲取當前滑鼠位置
    thisPosX := 0
    thisPosY := 0
    MouseGetPos(&thisPosX, &thisPosY)
    
    ; 座標選項
    座標選項 := "使用F6前的滑鼠座標 [ " . thisPosX . " , " . thisPosY . " ]。`n如尚未指定，請按 ( Cancel )。`n正確指定座標後使用 ( F6 )。`n`n通貨1 = 1 (例:傳捲)`n通貨2 = 2 (例:知識捲)`n通貨3 = 3`n通貨4 = 4`n通貨5 = 5`n`n請依指示輸入對應的座標代號( 1 ~ 5 )"
    
    input_result := InputBox(座標選項, "F6快速取物定位", "w350 h280")
    
    if (input_result.Result = "OK") {
        affixID := input_result.Value

        ; 檢查輸入是否為 1-5 的數字
        if (affixID >= 1 and affixID <= 5) {
            ; 座標名稱對應
            PosX := ["通貨1_X", "通貨2_X", "通貨3_X", "通貨4_X", "通貨5_X"]
            PosY := ["通貨1_Y", "通貨2_Y", "通貨3_Y", "通貨4_Y", "通貨5_Y"]

            ; 使用固定配置檔案
            configFile := CONFIG_FILE

            ; 儲存座標
            try {
                IniWrite(thisPosX, configFile, "取物定位", PosX[affixID])
                IniWrite(thisPosY, configFile, "取物定位", PosY[affixID])

                ; 重新讀取取物設定
                讀取F6取物定位內容()

                ToolTip("通貨 " . affixID . " 座標設定完成！`n位置：(" . thisPosX . ", " . thisPosY . ")")
                SetTimer(() => ToolTip(), -3000)
            } catch Error as err {
                ToolTip("儲存座標失敗：" . err.Message)
                SetTimer(() => ToolTip(), -3000)
            }
        }
        else {
            ToolTip("請輸入正確的代號 1 ~ 5")
            SetTimer(() => ToolTip(), -3000)
        }
    }
}

; F6智能連續座標設置 - 新增功能
F6智能連續座標設置() {
    global F6座標設置中, F6當前設置編號, F6設置進度, CONFIG_FILE
    
    ; 初始化設置狀態
    F6座標設置中 := true
    F6當前設置編號 := 1
    F6設置進度 := Map()
    
    ; 啟用Enter和ESC熱鍵
    try {
        Hotkey("Enter", F6確認座標抓取, "On")
        Hotkey("Escape", F6取消座標設置, "On")
    } catch {
        ; 熱鍵可能已存在，忽略錯誤
    }
    
    ; 顯示初始引導
    F6顯示設置引導()
    
    ; 設置十字準心（使用與F7相同的機制）
    crossX := 0
    crossY := 0
    MouseGetPos(&crossX, &crossY)
    CreateCrosshair(crossX, crossY, "0xFF0000", 30, 4, 220, false)
}

; F6顯示設置引導
F6顯示設置引導() {
    global F6當前設置編號, F6設置進度
    
    ; 獲取當前滑鼠位置
    currentX := 0
    currentY := 0
    MouseGetPos(&currentX, &currentY)
    
    ; 設置項目對應
    設置項目 := Map(
        1, "通貨1 (例:傳捲)",
        2, "通貨2 (例:知識捲)", 
        3, "通貨3",
        4, "通貨4",
        5, "通貨5"
    )
    
    ; 計算已完成數量
    已完成數量 := F6設置進度.Count
    
    ; 構建引導文字
    引導文字 := "🎯 F6智能連續座標設置`n"
    引導文字 .= "━━━━━━━━━━━━━━━━━━━━━━━━`n"
    引導文字 .= "當前設置：" . 設置項目[F6當前設置編號] . " (" . F6當前設置編號 . "/5)`n"
    引導文字 .= "當前位置：(" . currentX . ", " . currentY . ")`n"
    引導文字 .= "進度：" . 已完成數量 . "/5 已完成`n"
    引導文字 .= "━━━━━━━━━━━━━━━━━━━━━━━━`n"
    引導文字 .= "操作說明：`n"
    引導文字 .= "• 移動滑鼠到目標物品上`n"
    引導文字 .= "• 按 [ENTER] 確認當前位置`n"
    引導文字 .= "• 按 [ESC] 取消設置並退出`n"
    
    ; 如果有已完成的項目，顯示列表
    if (已完成數量 > 0) {
        引導文字 .= "`n✅ 已完成項目：`n"
        for 編號, 資料 in F6設置進度 {
            項目名稱 := 設置項目[編號]
            引導文字 .= "   " . 項目名稱 . " → (" . 資料.x . ", " . 資料.y . ")`n"
        }
    }
    
    ; 顯示ToolTip（使用與系統一致的位置）
    ToolTip(引導文字, currentX + 15, currentY - 100)
}

; F6確認座標抓取
F6確認座標抓取(*) {
    global F6座標設置中, F6當前設置編號, F6設置進度, CONFIG_FILE
    
    if (!F6座標設置中) {
        return
    }
    
    ; 獲取當前滑鼠位置
    posX := 0
    posY := 0
    MouseGetPos(&posX, &posY)
    
    ; 使用固定配置檔案
    configFile := CONFIG_FILE
    
    ; 設置項目對應
    設置項目 := Map(
        1, "通貨1 (例:傳捲)",
        2, "通貨2 (例:知識捲)", 
        3, "通貨3",
        4, "通貨4",
        5, "通貨5"
    )
    
    配置鍵名 := Map(
        1, {x: "通貨1_X", y: "通貨1_Y"},
        2, {x: "通貨2_X", y: "通貨2_Y"},
        3, {x: "通貨3_X", y: "通貨3_Y"},
        4, {x: "通貨4_X", y: "通貨4_Y"},
        5, {x: "通貨5_X", y: "通貨5_Y"}
    )
    
    ; 儲存座標
    try {
        鍵名 := 配置鍵名[F6當前設置編號]
        IniWrite(posX, configFile, "取物定位", 鍵名.x)
        IniWrite(posY, configFile, "取物定位", 鍵名.y)
        
        ; 記錄到進度中
        F6設置進度[F6當前設置編號] := {x: posX, y: posY}
        
        ; 顯示成功指示器
        ShowSuccessIndicator(posX, posY, 設置項目[F6當前設置編號] . " 設定完成！")
        
        ; 準備下一個設置
        F6當前設置編號++
        
        ; 檢查是否完成所有設置
        if (F6當前設置編號 > 5) {
            ; 完成所有設置
            F6完成座標設置()
        } else {
            ; 繼續下一個設置
            F6顯示設置引導()
        }
        
    } catch Error as err {
        ; 顯示錯誤指示器
        ShowErrorIndicator(posX, posY, "座標儲存失敗")
        ShowToolTip("❌ 儲存座標失敗：" . err.Message, 3000, 1)
    }
}

; F6取消座標設置
F6取消座標設置(*) {
    global F6座標設置中
    
    if (!F6座標設置中) {
        return
    }
    
    ; 顯示取消訊息
    currentX := 0
    currentY := 0
    MouseGetPos(&currentX, &currentY)
    ShowToolTip("❌ F6座標設置已取消", 2000, 1)
    
    ; 結束設置
    F6結束座標設置()
}

; F6完成座標設置
F6完成座標設置() {
    global F6設置進度
    
    ; 重新讀取設定
    讀取F6取物定位內容()
    
    ; 顯示完成訊息
    完成訊息 := "🎉 F6座標設置完成！`n"
    完成訊息 .= "━━━━━━━━━━━━━━━━━━━━`n"
    for 編號, 資料 in F6設置進度 {
        設置項目 := Map(
            1, "通貨1 (例:傳捲)",
            2, "通貨2 (例:知識捲)", 
            3, "通貨3",
            4, "通貨4",
            5, "通貨5"
        )
        完成訊息 .= 設置項目[編號] . " → (" . 資料.x . ", " . 資料.y . ")`n"
    }
    完成訊息 .= "━━━━━━━━━━━━━━━━━━━━`n"
    完成訊息 .= "現在可以使用 F6 進行一鍵取物！"
    
    ShowToolTip(完成訊息, 5000, 1)
    
    ; 結束設置
    F6結束座標設置()
}

; F6結束座標設置
F6結束座標設置() {
    global F6座標設置中, F6當前設置編號, F6設置進度
    
    ; 重置狀態
    F6座標設置中 := false
    F6當前設置編號 := 1
    F6設置進度 := Map()
    
    ; 清除ToolTip
    ToolTip()
    
    ; 移除十字準心
    DestroyCrosshair()
    
    ; 停用熱鍵
    try {
        Hotkey("Enter", F6確認座標抓取, "Off")
        Hotkey("Escape", F6取消座標設置, "Off")
    } catch {
        ; 忽略錯誤
    }
}

; Win + F6 選單 (F6 取物選單)
F6_選單(*) {
    global F6取物模式, F6取物延遲
    
    ; 創建取物模式選擇GUI
    F6ModeGui := Gui("+AlwaysOnTop +Owner", "🎯 F6取物模式設置")
    F6ModeGui.BackColor := "0xF0F0F0"  ; 淺灰色背景
    F6ModeGui.MarginX := 15
    F6ModeGui.MarginY := 10
    F6ModeGui.SetFont("s12 Bold", "Microsoft JhengHei")
    
    ; 添加標題
    F6ModeGui.Add("Text", "w320 Center c0x000080", "🎯 F6一鍵取物模式設置")
    F6ModeGui.Add("Text", "w320 h1 0x10")  ; 更細分隔線
    
    ; 當前模式顯示（移到前面）
    F6ModeGui.SetFont("s10", "Microsoft JhengHei")
    ; 啟動智能連續設置
    啟動智能設置(*) {
        F6ModeGui.Destroy()  ; 關閉當前GUI
        F6智能連續座標設置()  ; 啟動智能設置
    }
    
    ; 按鈕區域
    F6ModeGui.SetFont("s11 Bold", "Microsoft JhengHei")
    
    ; 新增智能連續設置按鈕
    F6ModeGui.Add("Text", "w320 h5")  ; 間距
    F6ModeGui.SetFont("s11 Bold", "Microsoft JhengHei")
    F6ModeGui.Add("Button", "w320 h35 c0xFFFFFF Background0x00A000", "🚀 智能連續座標設置").OnEvent("Click", 啟動智能設置)
    F6ModeGui.SetFont("s9", "Microsoft JhengHei")
    F6ModeGui.Add("Text", "w320 Center c0x666666", "💡 無需開關面板，ENTER確認，ESC取消")
    
    ; 延遲設定區域
    F6ModeGui.Add("Text", "w320 h1 0x10")  ; 更細分隔線
    F6ModeGui.SetFont("s10", "Microsoft JhengHei")
    F6ModeGui.Add("Text", "w320", "⏱️ 取物延遲設定 (10-500ms)：")
    延遲Edit := F6ModeGui.Add("Edit", "w320 h20 Number", F6取物延遲)
    
    設定延遲(*) {
        new_delay := 延遲Edit.Value
        if (new_delay >= 10 && new_delay <= 500) {
            F6取物延遲 := new_delay
            
            ; 使用固定配置檔案
            configFile := CONFIG_FILE
            IniWrite(F6取物延遲, configFile, "取物設定", "F6取物延遲")
            ShowToolTip("延遲設定為 " . F6取物延遲 . "ms", 1500)
            F6ModeGui.Destroy()  ; 自動關閉GUI
        } else {
            ShowToolTip("延遲必須在10-500ms範圍內", 2000)
        }
    }
    
    F6ModeGui.Add("Button", "w320 h25 cGreen", "✅ 確認延遲設定").OnEvent("Click", 設定延遲)
    
    ; 計算螢幕置中位置並顯示 - 增加高度以容納新按鈕
    螢幕寬度 := A_ScreenWidth
    螢幕高度 := A_ScreenHeight
    GUI寬度 := 350
    GUI高度 := 420  ; 增加高度以容納新功能
    置中X := (螢幕寬度 - GUI寬度) // 2
    置中Y := (螢幕高度 - GUI高度) // 2
    F6ModeGui.Show("w" . GUI寬度 . " h" . GUI高度 . " x" . 置中X . " y" . 置中Y)
}

; ========================== F7 座標設置功能 ==========================

; F7 座標設置 - 現代化GUI版本
F7_座標設置(*) {
    global
    
    ; 🎮 第一步：激活遊戲視窗，確保座標正確
    try {
        ; 嘗試激活流亡黯道遊戲視窗
        if (WinExist("Path of Exile")) {
            WinActivate("Path of Exile")
            Sleep(100)  ; 等待視窗激活
        } else if (WinExist("Path of Exile 2")) {
            WinActivate("Path of Exile 2")
            Sleep(100)  ; 等待視窗激活
        } else {
            ; 沒有找到遊戲視窗，顯示提示
            ShowToolTip("❌ 未找到流亡黯道遊戲視窗！`n請確保遊戲正在運行", 4000, 1)
            return
        }
    } catch {
        ShowToolTip("❌ 激活遊戲視窗失敗！", 3000, 1)
        return
    }
    
    ; 🎯 第二步：確認遊戲視窗為活躍狀態後，抓取座標
    if (檢查遊戲視窗()) {
        ; 獲取當前滑鼠位置和顏色（現在確保是遊戲內的座標）
    thisPosX := 0
    thisPosY := 0
    MouseGetPos(&thisPosX, &thisPosY)
        colorabc := PixelGetColor(thisPosX, thisPosY)
        
        ; 確保座標是數字類型
        thisPosX := Integer(thisPosX)
        thisPosY := Integer(thisPosY)
        
        ; 創建美化的GUI面板（會自動處理十字準心）
        CreateF7CoordinateGUI(thisPosX, thisPosY, colorabc)
    } else {
        ShowToolTip("❌ 請在遊戲視窗中使用 F7 功能！", 3000, 1)
    }
}

; F7事件處理函數
HandleF7Confirm(*) {
    global
    ; 停止實時更新計時器
    if (F7UpdateTimer) {
        SetTimer(F7UpdateTimer, 0)
        F7UpdateTimer := ""
    }
    ProcessF7CoordinateInput(F7PosX, F7PosY, F7Color, F7CoordGUI)
}

HandleF7Cancel(*) {
    global
    ; 停止實時更新計時器
    if (F7UpdateTimer) {
        SetTimer(F7UpdateTimer, 0)
        F7UpdateTimer := ""
    }
    DestroyCrosshair()
    F7CoordGUI.Destroy()
}

; 創建F7座標定位GUI
CreateF7CoordinateGUI(posX, posY, color) {
    global F7CoordGUI, F7CoordInput, F7PosX, F7PosY, F7Color
    global CoordText, ColorText, ColorPreview, F7UpdateTimer
    
    ; 如果已存在GUI，先關閉並清理
    try {
        if (F7CoordGUI) {
            DestroyCrosshair()  ; 清理舊的十字準心
            F7CoordGUI.Destroy()  ; 關閉舊GUI
            Sleep(50)  ; 短暫延遲確保清理完成
        }
    } catch {
        ; 忽略關閉錯誤，繼續創建新GUI
    }
    
    ; 儲存參數到全域變數
    F7PosX := posX
    F7PosY := posY
    F7Color := color
    
    ; 安全的參數類型轉換
    posX := (IsObject(posX) && posX.Length > 0) ? posX[1] : posX
    posY := (IsObject(posY) && posY.Length > 0) ? posY[1] : posY
    
    ; 確保都是數字
    posX := IsNumber(posX) ? Integer(posX) : 0
    posY := IsNumber(posY) ? Integer(posY) : 0
    
    ; 創建新的十字準心指示器
    CreateCrosshair(posX, posY, "0xFF0000", 30, 4, 220, false)  ; autoClose = false
    
    ; 創建GUI - 調整尺寸以容納更大字體
    F7CoordGUI := Gui("+Resize +MaximizeBox", "🎯 F7背包定位工具 - Sid流亡工具箱")
    F7CoordGUI.BackColor := "0x2D2D30"
    F7CoordGUI.MarginX := 20
    F7CoordGUI.MarginY := 20
    
    ; 設定字體
    F7CoordGUI.SetFont("s14 Bold", "Microsoft YaHei UI")
    
    ; 標題區域 - 置中對齊
    TitleText := F7CoordGUI.Add("Text", "x20 y20 w640 h50 Center c0xFFFFFF", "🎯 F7背包座標定位與記錄工具")
    TitleText.SetFont("s20 Bold")
    
    ; 當前座標信息區域 - 重新排版，添加顏色預覽
    F7CoordGUI.SetFont("s14 Bold", "Microsoft YaHei UI")
    F7CoordGUI.Add("Text", "x35 y85 w500 h25 c0xFFFFFF", "📍 當前座標資訊")
    
    F7CoordGUI.SetFont("s12", "Consolas")
    CoordText := F7CoordGUI.Add("Text", "x35 y115 w400 h25 c0x00FF00", "座標位置: (" . posX . ", " . posY . ")")
    ColorText := F7CoordGUI.Add("Text", "x35 y140 w400 h25 c0x00CCFF", "顏色代碼: " . color)
    
    ; 即時顏色預覽小方格
    ColorPreview := F7CoordGUI.Add("Text", "x450 y125 w60 h30 Center c0x000000 Background" . color, "")
    ColorPreview.SetFont("s8", "Microsoft YaHei UI")
    F7CoordGUI.Add("Text", "x520 y130 w100 h20 c0xC0C0C0", "顏色預覽")
    F7CoordGUI.SetFont("s8", "Microsoft YaHei UI")
    
    ; 啟動實時更新計時器
    F7UpdateTimer := SetTimer(UpdateF7Display, 100)  ; 每100ms更新一次
    
    ; 背包相關偵測點 - 調整間距
    F7CoordGUI.SetFont("s14 Bold", "Microsoft YaHei UI")
    F7CoordGUI.Add("Text", "x35 y185 w600 h25 c0xFFFFFF", "🎮 背包相關偵測點")
    
    ; 注意事項 - 調整位置和間距
    F7CoordGUI.SetFont("s10", "Microsoft YaHei UI")
    F7CoordGUI.Add("Text", "x35 y215 w600 h20 c0xFFB366", "💡 注意：請先將滑鼠移動到需抓取的座標，再次使用F7! (紅十字為當前抓取到的座標)")
    
    ; 座標設置狀態與代號說明 - 調整間距
    F7CoordGUI.SetFont("s14 Bold", "Microsoft YaHei UI")
    F7CoordGUI.Add("Text", "x35 y250 w600 h25 c0xFFFFFF", "📋 背包座標設置狀態與代號說明")
    
    F7CoordGUI.SetFont("s11", "Microsoft YaHei UI")
    ; 檢查背包座標設置狀態
    個人背包狀態 := (背包左上_X != "error" && 背包左上_Y != "error" && 背包右下_X != "error" && 背包右下_Y != "error") ? "✅ 已設置" : "❌ 未設置"
    對方背包狀態 := (對方背包左上_X != "error" && 對方背包左上_Y != "error" && 對方背包右下_X != "error" && 對方背包右下_Y != "error") ? "✅ 已設置" : "❌ 未設置"
    交易按鈕狀態 := (接受交易_X != "error" && 接受交易_Y != "error") ? "✅ 已設置" : "❌ 未設置"
    
    ; 背包相關座標 (藍色系) - 調整間距和對齊
    BackpackLabel := F7CoordGUI.Add("Text", "x35 y285 w150 h22 c0x4A90E2", "📦 背包座標:")
    BackpackLabel.SetFont("s12 Bold")
    
    個人背包狀態顏色 := (個人背包狀態 = "✅ 已設置") ? "0x00FF00" : "0xFF6666"
    F7CoordGUI.Add("Text", "x190 y285 w250 h22 c0xC0C0C0", "1 = 背包左上角")
    F7CoordGUI.Add("Text", "x480 y285 w150 h22 c" . 個人背包狀態顏色, 個人背包狀態)
    
    F7CoordGUI.Add("Text", "x190 y310 w250 h22 c0xC0C0C0", "2 = 背包右下角")
    
    ; 交易相關座標 (綠色系) - 調整間距
    TradeLabel := F7CoordGUI.Add("Text", "x35 y345 w150 h22 c0x50C878", "🤝 交易座標:")
    TradeLabel.SetFont("s12 Bold")
    
    對方背包狀態顏色 := (對方背包狀態 = "✅ 已設置") ? "0x00FF00" : "0xFF6666"
    F7CoordGUI.Add("Text", "x190 y345 w250 h22 c0xC0C0C0", "3 = 對方背包左上")
    F7CoordGUI.Add("Text", "x480 y345 w150 h22 c" . 對方背包狀態顏色, 對方背包狀態)
    
    F7CoordGUI.Add("Text", "x190 y370 w250 h22 c0xC0C0C0", "4 = 對方背包右下")
    
    交易按鈕狀態顏色 := (交易按鈕狀態 = "✅ 已設置") ? "0x00FF00" : "0xFF6666"
    F7CoordGUI.Add("Text", "x190 y395 w250 h22 c0xC0C0C0", "5 = 接受交易")
    F7CoordGUI.Add("Text", "x480 y395 w150 h22 c" . 交易按鈕狀態顏色, 交易按鈕狀態)
    
      ; 功能可用性提示 - 調整位置和間距
    基本功能可用 := (個人背包狀態 = "✅ 已設置")
    交易功能可用 := (對方背包狀態 = "✅ 已設置" && 交易按鈕狀態 = "✅ 已設置")
    
    if (基本功能可用) {
        F7CoordGUI.Add("Text", "x35 y555 w300 h22 c0x00FF00", "🟢 基本背包功能：可使用")
    } else {
        F7CoordGUI.Add("Text", "x35 y555 w300 h22 c0xFF6666", "🚨 基本背包功能：需設置個人背包")
    }
    
    if (交易功能可用) {
        F7CoordGUI.Add("Text", "x345 y555 w270 h22 c0x00FF00", "🔵 交易功能：可使用")
    } else {
        F7CoordGUI.Add("Text", "x345 y555 w270 h22 c0xFF6666", "⚪ 交易功能：需設置相關座標")
    }
    
    ; 輸入區域標題 - 調整位置和間距
    F7CoordGUI.SetFont("s14 Bold", "Microsoft YaHei UI")
    F7CoordGUI.Add("Text", "x35 y590 w600 h25 c0xFFFFFF", "⌨️ 座標代號輸入")
    
    ; 輸入說明和輸入框 - 調整位置和對齊
    F7CoordGUI.SetFont("s12", "Microsoft YaHei UI")
    F7CoordGUI.Add("Text", "x35 y625 w220 h28 c0xFFFFFF", "請輸入座標代號:")
    
    ; 創建輸入框 - 調整位置和尺寸
    F7CoordInput := F7CoordGUI.Add("Edit", "x260 y623 w120 h32 Center c0x000000 Background0xFFFFFF")
    F7CoordInput.SetFont("s14 Bold", "Consolas")
    
    ; 輸入限制 - 調整位置，只允許1-8的數字
    F7CoordInput.OnEvent("Change", (*) => ValidateF7Input())
    
    F7CoordGUI.Add("Text", "x390 y625 w240 h28 c0xC0C0C0", "有效輸入: 1-7")
    
    ; 快速重新抓取提醒 - 在按鈕上方添加
    F7CoordGUI.SetFont("s10", "Microsoft YaHei UI")
    F7CoordGUI.Add("Text", "x35 y660 w610 h20 Center c0xFFD700", "💡 小提示：面板開啟時可直接按 F7 重新抓取當前滑鼠位置")
    
    ; 按鈕區域 - 調整位置和間距，保持居中
    F7CoordGUI.SetFont("s12 Bold", "Microsoft YaHei UI")
    ; 三個按鈕等寬排列，間距一致，底部居中
    btnWidth := 140
    btnHeight := 40
    btnY := 690
    btnSpacing := 30
    totalWidth := btnWidth * 3 + btnSpacing * 2
    startX := (680 - totalWidth) // 2
    ConfirmBtn := F7CoordGUI.Add("Button", "x" startX " y" btnY " w" btnWidth " h" btnHeight " c0xFFFFFF Background0x4CAF50 Default", "✅ 確定")
    CancelBtn := F7CoordGUI.Add("Button", "x" (startX+btnWidth+btnSpacing) " y" btnY " w" btnWidth " h" btnHeight " c0xFFFFFF Background0xF44336", "❌ 取消")
    OpenBagBtn := F7CoordGUI.Add("Button", "x" (startX+btnWidth*2+btnSpacing*2) " y" btnY " w" btnWidth " h" btnHeight " c0xFFFFFF Background0x2196F3", "📂 開啟背包")
    
    ; 按鈕事件
    ConfirmBtn.OnEvent("Click", HandleF7Confirm)
    CancelBtn.OnEvent("Click", HandleF7Cancel)
    OpenBagBtn.OnEvent("Click", OpenBagToGame)

OpenBagToGame(*) {
    if WinExist("Path of Exile") {
        WinActivate("Path of Exile")
        Sleep(100)
        Send("i")
        Sleep(200)
        F7CoordGUI.Show()
        F7CoordInput.Focus()
    } else if WinExist("Path of Exile 2") {
        WinActivate("Path of Exile 2")
        Sleep(100)
        Send("i")
        Sleep(200)
        F7CoordGUI.Show()
        F7CoordInput.Focus()
    } else {
        ShowToolTip("❌ 未找到遊戲視窗，請先啟動遊戲！", 3000, 1)
    }
}
    
    ; ESC 鍵關閉，Enter 鍵確認
    F7CoordGUI.OnEvent("Escape", HandleF7Cancel)
    F7CoordGUI.OnEvent("Close", HandleF7Cancel)
    
    ; 顯示GUI - 調整總高度以適應新增的提醒文字
    F7CoordGUI.Show("w680 h760")
    
    ; 自動聚焦到輸入框
    F7CoordInput.Focus()
}

; F7輸入驗證 - 只允許1-7的數字
ValidateF7Input(*) {
    global F7CoordInput
    
    currentText := F7CoordInput.Text
    if (currentText = "") {
        return
    }
    
    ; 過濾有效字符 (擴展到1-7)
    filteredText := ""
    Loop Parse, currentText {
        charCode := Ord(A_LoopField)
        ; 只允許數字1-7 (ASCII 49-55)
        if (charCode >= 49 && charCode <= 55) {
            filteredText .= A_LoopField
        }
    }
    
    ; 限制長度為1個字符
    if (StrLen(filteredText) > 1) {
        filteredText := SubStr(filteredText, 1, 1)
    }
    
    ; 更新輸入框內容
    if (filteredText != currentText) {
        F7CoordInput.Text := filteredText
        ; 保持游標在最後 - 修正為 AHK v2 語法
        F7CoordInput.Focus()
        textLen := StrLen(filteredText)
        SendMessage(0x00B1, textLen, textLen, F7CoordInput)  ; EM_SETSEL
    }
    
    ; 視覺反饋
    if (filteredText != "" && !IsValidF7Input(filteredText)) {
        F7CoordInput.Opt("+Background0xFFE6E6")  ; 淺紅色背景
    } else {
        F7CoordInput.Opt("+Background0xFFFFFF")  ; 白色背景
    }
}

; F7輸入驗證函數
IsValidF7Input(input) {
    ; 有效範圍為1-7
    if (IsInteger(input) && input >= 1 && input <= 7) {
        return true
    }
    return false
}

; 處理F7座標輸入
ProcessF7CoordinateInput(posX, posY, color, gui) {
    global F7CoordInput
    
    ; 安全的參數類型轉換
    posX := (IsObject(posX) && posX.Length > 0) ? posX[1] : posX
    posY := (IsObject(posY) && posY.Length > 0) ? posY[1] : posY
    
    ; 確保都是數字
    posX := IsNumber(posX) ? Integer(posX) : 0
    posY := IsNumber(posY) ? Integer(posY) : 0
    
    CoordID := F7CoordInput.Text
    
    if (!IsValidF7Input(CoordID)) {
        ; 顯示錯誤提示 - 使用 AHK v2 正確語法
        try {
            F7ErrorGUI := Gui("+AlwaysOnTop", "❌ 輸入錯誤")
            F7ErrorGUI.BackColor := "0x2D2D30"
            F7ErrorGUI.SetFont("s12", "Microsoft YaHei UI")
            F7ErrorGUI.Add("Text", "x25 y25 w300 h50 Center c0xFF6B6B", "❌ 請輸入正確的代號！`n有效輸入: 1-7")
            F7OKBtn := F7ErrorGUI.Add("Button", "x125 y85 w80 h30 c0xFFFFFF Background0xF44336", "確定")
            F7OKBtn.SetFont("s12 Bold")
            F7OKBtn.OnEvent("Click", (*) => F7ErrorGUI.Destroy())
            F7ErrorGUI.Show("w350 h130")
        } catch Error as err {
            ; 備用方案：使用 MsgBox
            MsgBox("❌ 請輸入正確的代號！`n有效輸入: 1-7", "輸入錯誤", "OK Icon!")
        }
        return
    }
    
    ; 關閉GUI並清理十字準心
    DestroyCrosshair()
    gui.Destroy()
    
    ; 已移除未實作的角色配置切換，固定使用 CONFIG_FILE
    configFile := CONFIG_FILE
    
    ; 座標配置對應表
    coordConfigs := Map(
        1, {xKey: "背包左上_X", yKey: "背包左上_Y", cKey: "背包左上_C", desc: "背包左上角"},
        2, {xKey: "背包右下_X", yKey: "背包右下_Y", cKey: "背包右下_C", desc: "背包右下角"},
        3, {xKey: "對方背包左上_X", yKey: "對方背包左上_Y", cKey: "對方背包左上_C", desc: "對方背包左上"},
        4, {xKey: "對方背包右下_X", yKey: "對方背包右下_Y", cKey: "對方背包右下_C", desc: "對方背包右下"},
        5, {xKey: "接受交易_X", yKey: "接受交易_Y", cKey: "接受交易_C", desc: "接受交易"}
    )
    
    ; 檢查輸入是否為 1-5 的數字
    CoordID := Integer(CoordID)
    if (CoordID >= 1 && CoordID <= 5 && coordConfigs.Has(CoordID)) {
        config := coordConfigs[CoordID]
        
        ; 轉換為字串避免陣列問題，並確保顏色格式統一
        xStr := String(posX)
        yStr := String(posY)
        ; 確保顏色以十六進制格式儲存，與NormalizeHex函數兼容
        colorStr := IsNumber(color) ? Format("0x{:06X}", color & 0xFFFFFF) : String(color)
        
        ; 儲存座標和顏色
        try {
            IniWrite(xStr, configFile, "背包定位", config.xKey)
            IniWrite(yStr, configFile, "背包定位", config.yKey)
            IniWrite(colorStr, configFile, "背包定位", config.cKey)
            
            ; 重新讀取設定並計算背包
            讀取F7背包定位內容()
            背包運算作業()
            
            ; 顯示成功指示器
            ShowSuccessIndicator(posX, posY, config.desc . " 設定完成！")
            
            ShowToolTip("✅ " . config.desc . " 設定完成！`n位置：(" . posX . ", " . posY . ")`n顏色：" . color, 3000, 1)
            
            ; 檢查是否為引導模式，如果是則自動返回設定精靈
            if (IsSet(設定引導模式) && 設定引導模式) {
                ; 取消引導模式並返回快速設定精靈
                SetTimer(引導完成返回精靈, -1500)  ; 延遲1.5秒讓使用者看到成功訊息
            }
        } catch Error as err {
            ; 顯示錯誤指示器
            ShowErrorIndicator(posX, posY, "座標儲存失敗")
            ShowToolTip("❌ 儲存座標失敗：" . err.Message, 3000, 1)
        }
    }
}

; Win + F7 說明
F7_說明(*) {
    ToolTip("本工具的 [Win + F7] 沒有多功能切換哦~ ^0^")
    SetTimer(() => ToolTip(), -3000)
}

; F7 實時座標與顏色更新函數
UpdateF7Display() {
    global CoordText, ColorText, ColorPreview, F7CoordGUI, F7PosX, F7PosY
    
    ; 檢查GUI是否還存在
    try {
        if (!F7CoordGUI) {
            return
        }
        
        ; 獲取當前滑鼠位置
    currentX := 0
    currentY := 0
    MouseGetPos(&currentX, &currentY)
        
        ; 檢查滑鼠是否在準心附近，避免讀取準心顏色
        crosshairRange := 20  ; 準心影響範圍
        isNearCrosshair := false
        
        ; 如果設定了準心位置，檢查是否接近
        if (IsSet(F7PosX) && IsSet(F7PosY)) {
            distance := Sqrt((currentX - F7PosX)**2 + (currentY - F7PosY)**2)
            if (distance <= crosshairRange) {
                isNearCrosshair := true
            }
        }
        
        ; 獲取當前位置的顏色（避免準心干擾）
        currentColor := 0
        currentColorHex := ""
        
        if (isNearCrosshair) {
            ; 如果接近準心，使用偏移位置讀取顏色
            offsetX := currentX + 25
            offsetY := currentY + 25
            currentColor := PixelGetColor(offsetX, offsetY)
            currentColorHex := Format("0x{:06X}", currentColor)
        } else {
            ; 正常讀取當前位置顏色
            currentColor := PixelGetColor(currentX, currentY)
            currentColorHex := Format("0x{:06X}", currentColor)
        }
        
        ; 更新座標文字
        if (CoordText) {
            try {
                CoordText.Text := "座標位置: (" . currentX . ", " . currentY . ")"
            }
        }
        
        ; 更新顏色文字，如果接近準心則顯示警告
        if (ColorText) {
            try {
                if (isNearCrosshair) {
                    ColorText.Text := "顏色代碼: " . currentColorHex . " (偏移讀取)"
                } else {
                    ColorText.Text := "顏色代碼: " . currentColorHex
                }
            }
        }
        
        ; 更新顏色預覽方格
        if (ColorPreview) {
            try {
                ; 設定新的背景顏色
                ColorPreview.Opt("Background" . currentColorHex)
                
                ; 根據顏色亮度決定文字顏色（深色背景用白字，淺色背景用黑字）
                r := (currentColor >> 16) & 0xFF
                g := (currentColor >> 8) & 0xFF
                b := currentColor & 0xFF
                brightness := (r * 0.299 + g * 0.587 + b * 0.114)
                textColor := brightness > 128 ? "0x000000" : "0xFFFFFF"
                ColorPreview.Opt("c" . textColor)
            }
        }
    } catch {
        ; 如果出錯，停止更新計時器
        return
    }
}

; 讀取F6取物定位內容
讀取F6取物定位內容() {
    global 通貨1X, 通貨1Y, 通貨2X, 通貨2Y, 通貨3X, 通貨3Y, 通貨4X, 通貨4Y, 通貨5X, 通貨5Y
    global F6取物延遲, F6取物模式, CONFIG_FILE
    
    ; 使用固定配置檔案
    configFile := CONFIG_FILE
    
    try {
    ; 讀取取物座標配置並同步為有/無下劃線兩種變數（為了兼容歷史代碼）
    通貨1X := (IniRead(configFile, "取物定位", "通貨1_X", 100) + 0)
    通貨1Y := (IniRead(configFile, "取物定位", "通貨1_Y", 100) + 0)
    通貨2X := (IniRead(configFile, "取物定位", "通貨2_X", 100) + 0)
    通貨2Y := (IniRead(configFile, "取物定位", "通貨2_Y", 100) + 0)
    通貨3X := (IniRead(configFile, "取物定位", "通貨3_X", 100) + 0)
    通貨3Y := (IniRead(configFile, "取物定位", "通貨3_Y", 100) + 0)
    通貨4X := (IniRead(configFile, "取物定位", "通貨4_X", 100) + 0)
    通貨4Y := (IniRead(configFile, "取物定位", "通貨4_Y", 100) + 0)
    通貨5X := (IniRead(configFile, "取物定位", "通貨5_X", 100) + 0)
    通貨5Y := (IniRead(configFile, "取物定位", "通貨5_Y", 100) + 0)

    ; 同步帶下劃線的變數名（某些舊代碼使用這些名稱）
    通貨1_X := 通貨1X
    通貨1_Y := 通貨1Y
    通貨2_X := 通貨2X
    通貨2_Y := 通貨2Y
    通貨3_X := 通貨3X
    通貨3_Y := 通貨3Y
    通貨4_X := 通貨4X
    通貨4_Y := 通貨4Y
    通貨5_X := 通貨5X
    通貨5_Y := 通貨5Y
        
        ; 讀取其他取物設定
        F6取物延遲 := IniRead(configFile, "取物設定", "F6取物延遲", 20)
        F6取物模式 := IniRead(configFile, "取物設定", "F6取物模式", 1)
        
    } catch Error as err {
        ; 設定預設值
        通貨1X := 100, 通貨1Y := 100
        通貨2X := 100, 通貨2Y := 100
        通貨3X := 100, 通貨3Y := 100
        通貨4X := 100, 通貨4Y := 100
        通貨5X := 100, 通貨5Y := 100
        F6取物延遲 := 20
        F6取物模式 := 1
    }
}

; 讀取F7背包定位內容
讀取F7背包定位內容() {
    global
    ; 使用固定配置檔案（移除角色切換）
    configFile := CONFIG_FILE
    
    try {
        背包左上_X := IniRead(configFile, "背包定位", "背包左上_X", "error")
        背包左上_Y := IniRead(configFile, "背包定位", "背包左上_Y", "error")
        背包右下_X := IniRead(configFile, "背包定位", "背包右下_X", "error")
        背包右下_Y := IniRead(configFile, "背包定位", "背包右下_Y", "error")
        對方背包左上_X := IniRead(configFile, "背包定位", "對方背包左上_X", "error")
        對方背包左上_Y := IniRead(configFile, "背包定位", "對方背包左上_Y", "error")
        對方背包右下_X := IniRead(configFile, "背包定位", "對方背包右下_X", "error")
        對方背包右下_Y := IniRead(configFile, "背包定位", "對方背包右下_Y", "error")
        接受交易_X := IniRead(configFile, "背包定位", "接受交易_X", "error")
        接受交易_Y := IniRead(configFile, "背包定位", "接受交易_Y", "error")
    } catch Error as err {
        ; 讀取失敗時保持預設值
    }
}

; 背包運算作業
背包運算作業() {
    global
    try {
        if (背包左上_X != "error" and 背包右下_X != "error") {
            掃描開始左上_X := Integer(背包左上_X)
            掃描開始左上_Y := Integer(背包左上_Y)
            掃描開始右下_X := Integer(背包右下_X)
            掃描開始右下_Y := Integer(背包右下_Y)
            掃描水平數量 := 12
            掃描垂直數量 := 5
            
            ; 計算每格的寬度和高度
            背包每格寬 := Floor((掃描開始右下_X - 掃描開始左上_X) / 掃描水平數量)
            背包每格高 := Floor((掃描開始右下_Y - 掃描開始左上_Y) / 掃描垂直數量)
        }
    } catch Error as err {
        ; 計算失敗時保持預設值
        背包每格寬 := 0
        背包每格高 := 0
    }
}

; GUI面板函數
功能說明(*) {
    功能介紹GUI := Gui("+Resize -MinimizeBox", "🎮 SID 流亡工具箱 V2 - 完整功能介紹")
    功能介紹GUI.BackColor := "0xF0F4F8"  ; 現代化淺藍背景
    功能介紹GUI.MarginX := 25
    功能介紹GUI.MarginY := 20

    ; 創建分頁控制器
    TabCtrl := 功能介紹GUI.Add("Tab3", "x20 y20 w760 h600 c0x2C3E50 Background0xFFFFFF", ["基礎功能", "交易輔助", "進階功能", "快速入門"])
    
    ; === 第一個分頁：基礎功能 ===
    TabCtrl.UseTab(1)
    
    ; 標題區域
    功能介紹GUI.SetFont("s16 Bold", "Microsoft YaHei UI")
    功能介紹GUI.Add("Text", "x40 y60 w700 h30 Center c0x2C3E50", "🎮 基礎遊戲功能")
    功能介紹GUI.Add("Text", "x40 y95 w700 h2 Background0x3498DB")
    
    ; F1-F12 基礎功能
    功能介紹GUI.SetFont("s12 Bold", "Microsoft YaHei UI")
    功能介紹GUI.Add("Text", "x60 y115 w320 h25 c0x27AE60", "📋 核心熱鍵功能 (F1-F12)")
    
    功能介紹GUI.SetFont("s10", "Microsoft YaHei UI")
    BasicFunctions := "🔄 [F1] 原始功能 / 返回角色選擇`n"
    BasicFunctions .= "💬 [F2] 暫離 / 勿擾 / 自動回復模式`n"
    BasicFunctions .= "🎒 [F3] 智能清包功能 (支援多種模式)`n"
    BasicFunctions .= "🚧 [F4] 功能開發中`n"
    BasicFunctions .= "🏠 [F5] 快速返回藏身處`n"
    BasicFunctions .= "🎯 [F6] 一鍵取物 (支援連續座標)`n"
    BasicFunctions .= "📍 [F7] 背包座標定位設置`n"
    BasicFunctions .= "🎲 [F8] 智能拾取功能`n"
    BasicFunctions .= "⏸️ [F9] 暫停/恢復工具`n"
    BasicFunctions .= "💚 [F10] 狀態偵測與喝水`n"
    BasicFunctions .= "🔄 [F11] 重新載入腳本`n"
    BasicFunctions .= "❌ [F12] 結束工具"
    
    功能介紹GUI.Add("Text", "x65 y145 w315 h280 c0x2C3E50", BasicFunctions)
    
    ; 系統控制功能
    功能介紹GUI.SetFont("s12 Bold", "Microsoft YaHei UI")
    功能介紹GUI.Add("Text", "x400 y115 w320 h25 c0xE74C3C", "⚙️ 系統控制功能")
    
    功能介紹GUI.SetFont("s10", "Microsoft YaHei UI")
    SystemFunctions := "�️ [Win+Z] 主功能選單`n"
    SystemFunctions .= "💰 [Win+V] 智能查價功能`n"
    SystemFunctions .= "📍 [Win+C] 座標抓取工具`n"
    SystemFunctions .= "⚔️ [Insert] 循環技能模式`n"
    SystemFunctions .= "🔧 [Win+X] 滑鼠連點設置`n"
    SystemFunctions .= "💻 [Win+K] 複製硬碟序號`n"
    SystemFunctions .= "🔧 [Ctrl+Shift+F12] 強制釋放按鍵"
    
    功能介紹GUI.Add("Text", "x405 y145 w315 h200 c0x2C3E50", SystemFunctions)
    
    ; 特殊說明
    功能介紹GUI.SetFont("s11 Bold", "Microsoft YaHei UI")
    功能介紹GUI.Add("Text", "x60 y450 w660 h25 c0xF39C12", "💡 重要提示")
    功能介紹GUI.SetFont("s10", "Microsoft YaHei UI")
    ImportantNotes := "• 所有功能都經過遊戲視窗檢測，僅在 Path of Exile 和 Path of Exile 2 中運作`n"
    ImportantNotes .= "• 工具會自動保存您的個人化設定"
    功能介紹GUI.Add("Text", "x65 y480 w655 h80 c0x8E44AD", ImportantNotes)
    
    ; === 第二個分頁：交易輔助 ===
    TabCtrl.UseTab(2)
    
    功能介紹GUI.SetFont("s16 Bold", "Microsoft YaHei UI")
    功能介紹GUI.Add("Text", "x40 y60 w700 h30 Center c0x2C3E50", "💱 快速交易輔助系統")
    功能介紹GUI.Add("Text", "x40 y95 w700 h2 Background0xE74C3C")
    
    ; 交易熱鍵
    功能介紹GUI.SetFont("s12 Bold", "Microsoft YaHei UI")
    功能介紹GUI.Add("Text", "x60 y115 w320 h25 c0xE74C3C", "🤝 快速交易熱鍵")
    
    功能介紹GUI.SetFont("s10", "Microsoft YaHei UI")
    TradeFunctions := "👥 [End] 快速申請組隊`n"
    TradeFunctions .= "   自動發送組隊邀請訊息`n`n"
    TradeFunctions .= "🤝 [Home] 快速申請交易`n"
    TradeFunctions .= "   自動發送交易請求訊息`n`n"
    TradeFunctions .= "✅ [PgUp] 確認交易欄位`n"
    TradeFunctions .= "   檢查交易物品是否正確`n`n"
    TradeFunctions .= "✅ [PgDn] 接受交易`n"
    TradeFunctions .= "   最終確認並完成交易"
    
    功能介紹GUI.Add("Text", "x65 y145 w315 h280 c0x2C3E50", TradeFunctions)
    
    ; 查價功能
    功能介紹GUI.SetFont("s12 Bold", "Microsoft YaHei UI")
    功能介紹GUI.Add("Text", "x400 y115 w320 h25 c0x27AE60", "💰 智能查價系統")
    
    功能介紹GUI.SetFont("s10", "Microsoft YaHei UI")
    PriceFunctions := "� [Win+V] 物品查價`n"
    PriceFunctions .= "   支援多種查價方式：`n"
    PriceFunctions .= "   • 遊戲內快速查價`n"
    PriceFunctions .= "   • 外部查價工具整合`n"
    PriceFunctions .= "   • 自動複製物品資訊`n`n"
    PriceFunctions .= "📋 使用說明：`n"
    PriceFunctions .= "   1. 將滑鼠移到要查價的物品上`n"
    PriceFunctions .= "   2. 按下 Win+V 執行查價`n"
    PriceFunctions .= "   3. 工具會自動處理查價流程`n`n"
    PriceFunctions .= "🔗 建議搭配 rchin-poe-trade 使用"
    
    功能介紹GUI.Add("Text", "x405 y145 w315 h280 c0x2C3E50", PriceFunctions)
    
    ; 交易流程說明
    功能介紹GUI.SetFont("s11 Bold", "Microsoft YaHei UI")
    功能介紹GUI.Add("Text", "x60 y450 w660 h25 c0xF39C12", "📋 標準交易流程")
    功能介紹GUI.SetFont("s10", "Microsoft YaHei UI")
    TradeFlow := "1. [End] 申請組隊 → 2. [Home] 申請交易 → 3. [PgUp] 確認物品 → 4. [PgDn] 完成交易"
    功能介紹GUI.Add("Text", "x65 y480 w655 h40 c0x8E44AD", TradeFlow)
    
    ; === 第三個分頁：進階功能 ===
    TabCtrl.UseTab(3)
    
    功能介紹GUI.SetFont("s16 Bold", "Microsoft YaHei UI")
    功能介紹GUI.Add("Text", "x40 y60 w700 h30 Center c0x2C3E50", "⚡ 進階自動化功能")
    功能介紹GUI.Add("Text", "x40 y95 w700 h2 Background0x8E44AD")
    
    ; 循環技能系統
    功能介紹GUI.SetFont("s12 Bold", "Microsoft YaHei UI")
    功能介紹GUI.Add("Text", "x60 y115 w320 h25 c0x8E44AD", "⚔️ 循環技能系統")
    
    功能介紹GUI.SetFont("s10", "Microsoft YaHei UI")
    SkillFunctions := "🔄 [Insert] 開啟/關閉循環`n"
    SkillFunctions .= "   支援 5 個技能位置 (Q/W/E/R/T)`n`n"
    SkillFunctions .= "⚙️ 設定功能：`n"
    SkillFunctions .= "   • 自訂技能按鍵`n"
    SkillFunctions .= "   • 設定釋放間隔時間`n"
    SkillFunctions .= "   • 開關特定技能位置`n`n"
    SkillFunctions .= "💡 使用方式：`n"
    SkillFunctions .= "   透過 Win+Z 選單進行設定`n"
    SkillFunctions .= "   設定完成後按 Insert 啟用"
    
    功能介紹GUI.Add("Text", "x65 y145 w315 h280 c0x2C3E50", SkillFunctions)
    
    ; 狀態偵測與自動化
    功能介紹GUI.SetFont("s12 Bold", "Microsoft YaHei UI")
    功能介紹GUI.Add("Text", "x400 y115 w320 h25 c0x27AE60", "💚 狀態偵測系統")
    
    功能介紹GUI.SetFont("s10", "Microsoft YaHei UI")
    StatusFunctions := "💊 [F10] 狀態偵測功能`n"
    StatusFunctions .= "   • 自動偵測生命值/魔力值`n"
    StatusFunctions .= "   • 低血量自動喝水`n"
    StatusFunctions .= "   • 支援多種藥劑設定`n`n"
    StatusFunctions .= "�️ 滑鼠連點功能`n"
    StatusFunctions .= "   • [滾輪下壓] 連點模式`n"
    StatusFunctions .= "   • [Ctrl+左鍵] 連點模式`n"
    StatusFunctions .= "   • 可調整連點速度`n`n"
    StatusFunctions .= "🎯 [F8] 智能拾取`n"
    StatusFunctions .= "   • 自動拾取指定物品`n"
    StatusFunctions .= "   • 支援過濾設定"
    
    功能介紹GUI.Add("Text", "x405 y145 w315 h280 c0x2C3E50", StatusFunctions)
    
    ; 座標系統
    功能介紹GUI.SetFont("s11 Bold", "Microsoft YaHei UI")
    功能介紹GUI.Add("Text", "x60 y450 w660 h25 c0xF39C12", "� 座標設置系統")
    功能介紹GUI.SetFont("s10", "Microsoft YaHei UI")
    CoordFunctions := "透過 [Win+C] 開啟座標抓取工具，支援 F6、F7、F10 等功能的精確座標設定"
    功能介紹GUI.Add("Text", "x65 y480 w655 h40 c0x8E44AD", CoordFunctions)
    
    ; === 第四個分頁：快速入門 ===
    TabCtrl.UseTab(4)
    
    功能介紹GUI.SetFont("s16 Bold", "Microsoft YaHei UI")
    功能介紹GUI.Add("Text", "x40 y60 w700 h30 Center c0x2C3E50", "🚀 快速入門指南")
    功能介紹GUI.Add("Text", "x40 y95 w700 h2 Background0xF39C12")
    
    ; 新手指引
    功能介紹GUI.SetFont("s12 Bold", "Microsoft YaHei UI")
    功能介紹GUI.Add("Text", "x60 y115 w320 h25 c0xF39C12", "� 新手必讀")
    
    功能介紹GUI.SetFont("s10", "Microsoft YaHei UI")
    BeginnerGuide := "1️ 基本使用：`n"
    BeginnerGuide .= "   • 按 Win+Z 開啟主選單`n"
    BeginnerGuide .= "   • 探索各項功能設定`n`n"
    BeginnerGuide .= "2️ 推薦設定順序：`n"
    BeginnerGuide .= "   • 先設定 F2 回復模式`n"
    BeginnerGuide .= "   • 設定 F6 一鍵取物座標`n"
    BeginnerGuide .= "   • 設定 F10 狀態偵測`n`n"
    BeginnerGuide .= "3️ 常用功能：`n"
    BeginnerGuide .= "   • F1: 返回角色選擇`n"
    BeginnerGuide .= "   • F5: 返回藏身處`n"
    BeginnerGuide .= "   • Win+V: 查價功能"
    
    功能介紹GUI.Add("Text", "x65 y145 w315 h280 c0x2C3E50", BeginnerGuide)
    
    ; 進階技巧
    功能介紹GUI.SetFont("s12 Bold", "Microsoft YaHei UI")
    功能介紹GUI.Add("Text", "x400 y115 w320 h25 c0x27AE60", "💡 進階技巧")
    
    功能介紹GUI.SetFont("s10", "Microsoft YaHei UI")
    AdvancedTips := "⚡ 效率提升：`n"
    AdvancedTips .= "   • 搭配快速交易熱鍵`n"
    AdvancedTips .= "   • 設定循環技能提升刷圖效率`n"
    AdvancedTips .= "   • 使用狀態偵測自動喝水`n`n"
    AdvancedTips .= "� 自訂設定：`n"
    AdvancedTips .= "   • 調整各項功能參數`n"
    AdvancedTips .= "   • 設定個人化快捷鍵`n"
    AdvancedTips .= "   • 備份重要設定`n`n"
    AdvancedTips .= "⚠️ 注意事項：`n"
    AdvancedTips .= "   • 工具僅在遊戲視窗中運作`n"
    AdvancedTips .= "   • 支援 POE1 和 POE2`n"
    AdvancedTips .= "   • 遇到問題可按 F9 暫停工具"
    
    功能介紹GUI.Add("Text", "x405 y145 w315 h280 c0x2C3E50", AdvancedTips)
    
    ; 技術支援
    功能介紹GUI.SetFont("s11 Bold", "Microsoft YaHei UI")
    功能介紹GUI.Add("Text", "x60 y450 w660 h25 c0xE74C3C", "🆘 技術支援與更新")
    功能介紹GUI.SetFont("s10", "Microsoft YaHei UI")
    SupportInfo := "作者網站：保留中..."
    功能介紹GUI.Add("Text", "x65 y480 w655 h40 c0x8E44AD", SupportInfo)
    
    ; 回到主分頁
    TabCtrl.UseTab()
    
    ; 底部資訊
    功能介紹GUI.SetFont("s10 Bold", "Microsoft YaHei UI")
    功能介紹GUI.Add("Text", "x30 y635 w740 h20 Center c0x2C3E50", "🎮 SID 流亡工具箱 V2 - 讓遊戲更簡單，讓效率更提升！")

    ; 計算螢幕置中位置並顯示
    螢幕寬度 := A_ScreenWidth
    螢幕高度 := A_ScreenHeight
    GUI寬度 := 800
    GUI高度 := 680
    置中X := (螢幕寬度 - GUI寬度) // 2
    置中Y := (螢幕高度 - GUI高度) // 2
    功能介紹GUI.Show("w" . GUI寬度 . " h" . GUI高度 . " x" . 置中X . " y" . 置中Y)
}

; 啟動系統 - 科技感GUI
顯示啟動訊息() {
    ; 創建多分頁啟動畫面
    StartupGUI := Gui("+AlwaysOnTop -MinimizeBox -MaximizeBox +LastFound", "SID EXILE TOOLBOX - 啟動精靈")
    StartupGUI.BackColor := "0x0A0A0A"  ; 深黑背景
    StartupGUI.MarginX := 0
    StartupGUI.MarginY := 0
    
    ; 設置透明度
    WinSetTransparent(245, StartupGUI)
    
    ; 創建分頁控制器
    TabCtrl := StartupGUI.Add("Tab3", "x20 y20 w660 h500 c0xFFFFFF Background0x1A1A1A", ["歡迎使用", "功能概覽"])
    
    ; === 第一個分頁：歡迎使用 ===
    TabCtrl.UseTab(1)
    
    ; 主標題 - 科技藍色漸層效果
    StartupGUI.SetFont("s24 Bold", "Consolas")
    StartupGUI.Add("Text", "x50 y70 w600 h35 Center c0x00BFFF", "SID EXILE TOOLBOX")
    
    ; 副標題線條
    StartupGUI.SetFont("s12", "Microsoft YaHei UI")
    StartupGUI.Add("Text", "x50 y115 w600 h20 Center c0x4169E1", "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    
    ; 版本信息
    StartupGUI.SetFont("s16 Bold", "Consolas")
    StartupGUI.Add("Text", "x50 y145 w600 h30 Center c0x00FF7F", "V2 ULTIMATE EDITION")
    
    ; 系統狀態
    StartupGUI.SetFont("s11", "Consolas")
    StartupGUI.Add("Text", "x50 y185 w600 h20 Center c0xFFD700", "[ ✓ SYSTEM INITIALIZED ]")
    StartupGUI.Add("Text", "x50 y205 w600 h20 Center c0xFFD700", "[ ✓ GAME DETECTION READY ]")
    StartupGUI.Add("Text", "x50 y225 w600 h20 Center c0xFFD700", "[ ✓ HOTKEYS REGISTERED ]")
    StartupGUI.Add("Text", "x50 y245 w600 h20 Center c0xFFD700", "[ ✓ TRADING FUNCTIONS LOADED ]")
    
    ; 分隔線
    StartupGUI.Add("Text", "x50 y275 w600 h20 Center c0x4169E1", "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    
    ; 歡迎內容
    StartupGUI.SetFont("s14 Bold", "Microsoft YaHei UI")
    StartupGUI.Add("Text", "x50 y305 w600 h25 Center c0xFFFFFF", "🎮 歡迎使用流亡之路超級工具箱！")
    
    StartupGUI.SetFont("s11", "Microsoft YaHei UI")
    WelcomeText := "• 本工具專為 Path of Exile & Path of Exile 2 設計`n"
    WelcomeText .= "• 提供自動化遊戲輔助功能，提升遊戲體驗`n"
    WelcomeText .= "• 支援快速交易、技能循環、座標設置等功能`n"
    WelcomeText .= "• 所有功能都經過遊戲視窗檢測，確保安全使用`n`n"
    WelcomeText .= "💡 快速開始：使用 Win+Z 打開主選單探索所有功能"
    
    StartupGUI.Add("Text", "x70 y340 w560 h140 c0xC0C0C0", WelcomeText)
    
    ; === 第二個分頁：功能概覽 ===
    TabCtrl.UseTab(2)
    
    ; 功能概覽標題
    StartupGUI.SetFont("s18 Bold", "Microsoft YaHei UI")
    StartupGUI.Add("Text", "x50 y70 w600 h30 Center c0x00BFFF", "🛠️ 功能模組概覽")
    
    ; 分隔線
    StartupGUI.Add("Text", "x50 y110 w600 h2 Background0x4169E1")
    
    ; 功能列表
    StartupGUI.SetFont("s12 Bold", "Microsoft YaHei UI")
    
    ; 第一列功能
    StartupGUI.Add("Text", "x70 y130 w250 h25 c0x00FF7F", "🎯 核心功能")
    StartupGUI.SetFont("s10", "Microsoft YaHei UI")
    CoreFunctions := "• F1-F12: 各種遊戲輔助功能`n• Win+Z: 主功能選單`n• Win+V: 智能查價`n• Win+C: 座標抓取工具"
    StartupGUI.Add("Text", "x75 y155 w250 h90 c0xC0C0C0", CoreFunctions)
    
    StartupGUI.SetFont("s12 Bold", "Microsoft YaHei UI")
    StartupGUI.Add("Text", "x370 y130 w250 h25 c0x00FF7F", "⚡ 自動化功能")
    StartupGUI.SetFont("s10", "Microsoft YaHei UI")
    AutoFunctions := "• 循環技能系統`n• 自動喝水偵測`n• 滑鼠連點功能`n• 背包清理輔助"
    StartupGUI.Add("Text", "x375 y155 w250 h90 c0xC0C0C0", AutoFunctions)
    
    ; 第二列功能
    StartupGUI.SetFont("s12 Bold", "Microsoft YaHei UI")
    StartupGUI.Add("Text", "x70 y260 w250 h25 c0x00FF7F", "💱 交易功能")
    StartupGUI.SetFont("s10", "Microsoft YaHei UI")
    TradeFunctions := "• End: 快速組隊`n• Home: 交易輔助`n• PgUp: 確認交易`n• PgDn: 接受交易"
    StartupGUI.Add("Text", "x75 y285 w250 h90 c0xC0C0C0", TradeFunctions)
    
    StartupGUI.SetFont("s12 Bold", "Microsoft YaHei UI")
    StartupGUI.Add("Text", "x370 y260 w250 h25 c0x00FF7F", "🔧 設定功能")
    StartupGUI.SetFont("s10", "Microsoft YaHei UI")
    SettingFunctions := "• 智能座標設置`n• 功能開關控制`n• 個人化設定`n• 即時配置儲存"
    StartupGUI.Add("Text", "x375 y285 w250 h90 c0xC0C0C0", SettingFunctions)
    
    ; 重要提示區域
    StartupGUI.SetFont("s11 Bold", "Microsoft YaHei UI")
    StartupGUI.Add("Text", "x50 y370 w600 h20 Center c0xFFD700", "⚠️ 重要提示")
    StartupGUI.SetFont("s10", "Microsoft YaHei UI")
    WarningText := "• 本工具僅在 Path of Exile 和 Path of Exile 2 視窗中運作`n"
    WarningText .= "• 首次使用建議先查看功能說明，了解各項功能用途`n"
    WarningText .= "• 所有功能都可透過 Win+Z 主選單進行設定和調整"
    StartupGUI.Add("Text", "x70 y400 w560 h80 c0xFFFF00", WarningText)
    
    ; 回到分頁控制
    TabCtrl.UseTab()
    
    ; 科技邊框效果
    StartupGUI.Add("Text", "x10 y10 w680 h2 Background0x00BFFF")  ; 上邊框
    StartupGUI.Add("Text", "x10 y628 w680 h2 Background0x00BFFF") ; 下邊框
    StartupGUI.Add("Text", "x10 y10 w2 h620 Background0x00BFFF")  ; 左邊框
    StartupGUI.Add("Text", "x688 y10 w2 h620 Background0x00BFFF") ; 右邊框
    
    ; 底部操作區域
    StartupGUI.SetFont("s12 Bold", "Microsoft YaHei UI")
    global 操作提示文字 := StartupGUI.Add("Text", "x50 y550 w400 h25 c0xFFFFFF", "按 ENTER 開始使用工具，ESC 取消")
    
    ; 按鈕區域
    StartupGUI.SetFont("s11 Bold", "Microsoft YaHei UI")
    StartBtn := StartupGUI.Add("Button", "x450 y550 w100 h30 c0xFFFFFF Background0x00AA00", "✓ 開始使用")
    CancelBtn := StartupGUI.Add("Button", "x560 y550 w100 h30 c0xFFFFFF Background0xAA0000", "✗ 取消")
    
    ; 作者信息
    StartupGUI.SetFont("s9", "Consolas")
    StartupGUI.Add("Text", "x50 y590 w600 h25 Center c0x666666", "Developed by Sid | 流亡之路專用工具箱")
    
    ; 事件處理
    StartBtn.OnEvent("Click", (*) => 處理啟動按鈕())
    CancelBtn.OnEvent("Click", (*) => ExitApp())
    
    ; Enter 和 ESC 處理
    StartupGUI.OnEvent("Escape", (*) => ExitApp())
    
    ; 註冊 Enter 熱鍵
    HotKey("Enter", 啟動GUI_Enter處理, "On")
    
    ; 當GUI關閉時移除熱鍵
    StartupGUI.OnEvent("Close", 啟動GUI_關閉處理)
    
    ; 處理啟動按鈕的函數
    處理啟動按鈕() {
        StartupGUI.Destroy()
        ; 檢查是否為首次使用，觸發首次使用引導
        if (首次使用標記) {
            SetTimer(() => 顯示首次使用引導(), -500)
        }
    }
    
    ; Enter 處理函數
    啟動GUI_Enter處理(*) {
        try {
            HotKey("Enter", "Off")
            ; 停止動畫
            SetTimer(操作提示文字動畫, 0)
        } catch {
            ; 忽略錯誤
        }
        StartupGUI.Destroy()
        ; 檢查是否為首次使用，觸發首次使用引導
        if (首次使用標記) {
            SetTimer(() => 顯示首次使用引導(), -500)
        }
    }
    
    ; 關閉處理函數
    啟動GUI_關閉處理(*) {
        try {
            HotKey("Enter", "Off")
            ; 停止動畫
            SetTimer(操作提示文字動畫, 0)
        } catch {
            ; 忽略錯誤
        }
        ExitApp()
    }
    
    ; 居中顯示
    螢幕寬度 := A_ScreenWidth
    螢幕高度 := A_ScreenHeight
    GUI寬度 := 700
    GUI高度 := 640
    置中X := (螢幕寬度 - GUI寬度) // 2
    置中Y := (螢幕高度 - GUI高度) // 2
    
    StartupGUI.Show("w" . GUI寬度 . " h" . GUI高度 . " x" . 置中X . " y" . 置中Y)
    
    ; 啟動文字淡入淡出動態效果
    SetTimer(操作提示文字動畫, 120)
    
    ; 動態效果變數
    global 動畫階段 := 0
    global 動畫方向 := 1
    global 上次顏色代碼 := "0xFFFFFF"
    
    ; 文字動畫函數
    操作提示文字動畫() {
        global 動畫階段, 動畫方向, 操作提示文字, 上次顏色代碼
        
        ; 計算顏色 - 使用更平滑的變化
        紅色 := Round(200 + 55 * Sin(動畫階段 * 3.14159 / 180))
        綠色 := Round(200 + 55 * Sin((動畫階段 + 120) * 3.14159 / 180))
        藍色 := Round(200 + 55 * Sin((動畫階段 + 240) * 3.14159 / 180))
        
        ; 組合顏色代碼
        顏色代碼 := Format("0x{:06X}", (紅色 << 16) | (綠色 << 8) | 藍色)
        
        ; 只有當顏色真正改變時才更新，避免不必要的閃爍
        if (顏色代碼 != 上次顏色代碼) {
            try {
                操作提示文字.SetFont("c" . 顏色代碼)
                上次顏色代碼 := 顏色代碼
            } catch {
                ; 如果控制項不存在，停止動畫
                SetTimer(操作提示文字動畫, 0)
                return
            }
        }
        
        ; 更新動畫階段 - 更慢的速度
        動畫階段 += 3
        if (動畫階段 >= 360) {
            動畫階段 := 0
        }
    }
    
    ; 等待用戶操作，移除自動關閉
}

開啟作者網站(*) {
    Run("https://lelive.weebly.com/")
}

開啟查價網站(*) {
    Run("https://github.com/rChinnnn/rchin-poe-trade")
}

; 選單項目函數（簡化實現）
工具熱鍵列表說明(*) {
    熱鍵列表GUI := Gui("+Resize -MinimizeBox", "📋 SID 流亡工具箱 - 完整熱鍵列表")
    熱鍵列表GUI.BackColor := "0xF5F7FA"
    熱鍵列表GUI.MarginX := 20
    熱鍵列表GUI.MarginY := 15

    ; 創建分頁控制器
    TabCtrl := 熱鍵列表GUI.Add("Tab3", "x15 y15 w870 h650 c0x2C3E50 Background0xFFFFFF", ["基礎熱鍵", "系統控制", "交易輔助", "特殊功能"])
    
    ; === 第一個分頁：基礎熱鍵 (F1-F12) ===
    TabCtrl.UseTab(1)
    
    熱鍵列表GUI.SetFont("s16 Bold", "Microsoft YaHei UI")
    熱鍵列表GUI.Add("Text", "x40 y50 w800 h30 Center c0x2C3E50", "🎮 基礎功能熱鍵 (F1-F12)")
    熱鍵列表GUI.Add("Text", "x40 y85 w800 h2 Background0x3498DB")
    
    ; F1-F6 功能
    熱鍵列表GUI.SetFont("s12 Bold", "Microsoft YaHei UI")
    熱鍵列表GUI.Add("Text", "x60 y110 w390 h25 c0x27AE60", "🔧 核心遊戲功能 (F1-F6)")
    
    熱鍵列表GUI.SetFont("s11", "Microsoft YaHei UI")
    F1ToF6 := "🔄 [F1] 原始功能 / 返回角色選擇`n"
    F1ToF6 .= "   支援兩種模式切換，可透過 Win+F1 設定`n`n"
    F1ToF6 .= "💬 [F2] 暫離 / 勿擾 / 自動回復模式`n"
    F1ToF6 .= "   支援多種回復模式，可透過 Win+F2 設定`n`n"
    F1ToF6 .= "🎒 [F3] 智能清包功能`n"
    F1ToF6 .= "   支援多種清包模式，可透過 Win+F3 設定`n`n"
    F1ToF6 .= "🚧 [F4] 功能開發中`n"
    F1ToF6 .= "   預留功能位置，未來版本將加入新功能`n`n"
    F1ToF6 .= "🏠 [F5] 快速返回藏身處`n"
    F1ToF6 .= "   一鍵返回藏身處，支援各種場景`n`n"
    F1ToF6 .= "🎯 [F6] 一鍵取物功能`n"
    F1ToF6 .= "   支援連續座標設定，快速拾取指定位置物品"
    
    熱鍵列表GUI.Add("Text", "x65 y145 w385 h340 c0x2C3E50", F1ToF6)
    
    ; F7-F12 功能
    熱鍵列表GUI.SetFont("s12 Bold", "Microsoft YaHei UI")
    熱鍵列表GUI.Add("Text", "x470 y110 w390 h25 c0xE74C3C", "⚡ 進階功能 (F7-F12)")
    
    熱鍵列表GUI.SetFont("s11", "Microsoft YaHei UI")
    F7ToF12 := "📍 [F7] 背包座標定位設置`n"
    F7ToF12 .= "   設定背包相關座標，支援多種定位方式`n`n"
    F7ToF12 .= "🎲 [F8] 智能拾取功能`n"
    F7ToF12 .= "   自動拾取指定物品，支援過濾設定`n"
    F7ToF12 .= "   [Shift+F8] 開啟拾取設置介面`n`n"
    F7ToF12 .= "⏸️ [F9] 暫停/恢復工具`n"
    F7ToF12 .= "   暫停所有功能，恢復原始鍵盤`n`n"
    F7ToF12 .= "💚 [F10] 狀態偵測與自動喝水`n"
    F7ToF12 .= "   偵測生命值/魔力值，自動使用藥劑`n`n"
    F7ToF12 .= "🔄 [F11] 重新載入腳本`n"
    F7ToF12 .= "   重新啟動工具，重載所有設定`n`n"
    F7ToF12 .= "❌ [F12] 結束工具`n"
    F7ToF12 .= "   完全關閉工具，釋放系統資源"
    
    熱鍵列表GUI.Add("Text", "x475 y140 w385 h320 c0x2C3E50", F7ToF12)
    
    ; 特殊提示
    熱鍵列表GUI.SetFont("s11 Bold", "Microsoft YaHei UI")
    熱鍵列表GUI.Add("Text", "x60 y480 w780 h25 c0xF39C12", "💡 特殊功能說明")
    熱鍵列表GUI.SetFont("s10", "Microsoft YaHei UI")
    熱鍵列表GUI.Add("Text", "x65 y505 w775 h60 c0x8E44AD", "• 所有 F1-F12 功能都支援 Win+Fx 組合鍵來開啟設定選單`n• 部分功能支援 Shift+Fx 組合鍵來開啟進階設定`n• 工具會自動檢測遊戲視窗，僅在 Path of Exile 系列遊戲中運作")
    
    ; === 第二個分頁：系統控制 ===
    TabCtrl.UseTab(2)
    
    熱鍵列表GUI.SetFont("s16 Bold", "Microsoft YaHei UI")
    熱鍵列表GUI.Add("Text", "x40 y50 w800 h30 Center c0x2C3E50", "⚙️ 系統控制熱鍵")
    熱鍵列表GUI.Add("Text", "x40 y85 w800 h2 Background0xE74C3C")
    
    ; Win 組合鍵
    熱鍵列表GUI.SetFont("s12 Bold", "Microsoft YaHei UI")
    熱鍵列表GUI.Add("Text", "x60 y110 w390 h25 c0xE74C3C", "🔑 Windows 組合鍵")
    
    熱鍵列表GUI.SetFont("s11", "Microsoft YaHei UI")
    WinKeys := "🖱️ [Win+Z] 主功能選單`n"
    WinKeys .= "   開啟工具的主要功能選單，所有設定的入口`n`n"
    WinKeys .= "💰 [Win+V] 智能查價功能`n"
    WinKeys .= "   快速查價物品，支援多種查價方式`n`n"
    WinKeys .= "📍 [Win+C] 座標抓取工具`n"
    WinKeys .= "   通用座標設定工具，支援多項功能`n`n"
    WinKeys .= " [Win+K] 複製硬碟序號`n"
    WinKeys .= "   複製硬碟序號，用於技術支援`n`n"
    WinKeys .= "🔧 [Win+Fx] 功能設定選單`n"
    WinKeys .= "   針對特定 F 鍵功能開啟設定介面"
    
    熱鍵列表GUI.Add("Text", "x65 y140 w385 h340 c0x2C3E50", WinKeys)
    
    ; 特殊控制鍵
    熱鍵列表GUI.SetFont("s12 Bold", "Microsoft YaHei UI")
    熱鍵列表GUI.Add("Text", "x470 y110 w390 h25 c0x8E44AD", "🎯 特殊控制功能")
    
    熱鍵列表GUI.SetFont("s11", "Microsoft YaHei UI")
    SpecialKeys .= "⚔️ [Insert] 循環技能模式`n"
    SpecialKeys .= "   開啟/關閉技能循環系統`n`n"
    SpecialKeys .= "🔧 [Ctrl+Shift+F12] 強制釋放按鍵`n"
    SpecialKeys .= "   解決按鍵卡住問題，緊急釋放所有修飾鍵`n`n"
    SpecialKeys .= "🖱️ [滾輪下壓] 滑鼠連點`n"
    SpecialKeys .= "   按住滾輪中鍵啟動連點功能`n`n"
    SpecialKeys .= "🎮 各種監測熱鍵`n"
    SpecialKeys .= "   Enter、Ctrl+F、I 鍵等用於狀態監測"
    
    熱鍵列表GUI.Add("Text", "x475 y140 w385 h340 c0x2C3E50", SpecialKeys)
    
    ; === 第三個分頁：交易輔助 ===
    TabCtrl.UseTab(3)
    
    熱鍵列表GUI.SetFont("s16 Bold", "Microsoft YaHei UI")
    熱鍵列表GUI.Add("Text", "x40 y50 w800 h30 Center c0x2C3E50", "💱 快速交易輔助熱鍵")
    熱鍵列表GUI.Add("Text", "x40 y85 w800 h2 Background0x27AE60")
    
    ; 交易流程熱鍵
    熱鍵列表GUI.SetFont("s12 Bold", "Microsoft YaHei UI")
    熱鍵列表GUI.Add("Text", "x60 y110 w390 h25 c0x27AE60", "🤝 標準交易流程")
    
    熱鍵列表GUI.SetFont("s11", "Microsoft YaHei UI")
    TradeKeys := "👥 [End] 快速申請組隊`n"
    TradeKeys .= "   步驟 1：自動發送組隊邀請訊息`n"
    TradeKeys .= "   適用場景：開始交易前的組隊邀請`n`n"
    TradeKeys .= "🤝 [Home] 快速申請交易`n"
    TradeKeys .= "   步驟 2：自動發送交易請求訊息`n"
    TradeKeys .= "   適用場景：組隊完成後申請交易`n`n"
    TradeKeys .= "✅ [PgUp] 確認交易欄位`n"
    TradeKeys .= "   步驟 3：檢查交易視窗中的物品`n"
    TradeKeys .= "   適用場景：確認對方放入正確物品`n`n"
    TradeKeys .= "✅ [PgDn] 接受交易`n"
    TradeKeys .= "   步驟 4：最終確認並完成交易`n"
    TradeKeys .= "   適用場景：確認無誤後完成交易"
    
    熱鍵列表GUI.Add("Text", "x65 y140 w385 h300 c0x2C3E50", TradeKeys)
    
    ; 查價功能
    熱鍵列表GUI.SetFont("s12 Bold", "Microsoft YaHei UI")
    熱鍵列表GUI.Add("Text", "x470 y110 w390 h25 c0xF39C12", "💰 查價與輔助功能")
    
    熱鍵列表GUI.SetFont("s11", "Microsoft YaHei UI")
    PriceKeys := "💰 [Win+V] 物品查價`n"
    PriceKeys .= "   智能查價系統，支援多種查價方式：`n"
    PriceKeys .= "   • 遊戲內快速查價`n"
    PriceKeys .= "   • 外部查價工具整合`n"
    PriceKeys .= "   • 自動複製物品資訊`n`n"
    PriceKeys .= "使用方法：`n"
    PriceKeys .= "   1. 將滑鼠移到要查價的物品上`n"
    PriceKeys .= "   2. 按下 Win+V 執行查價`n"
    PriceKeys .= "   3. 工具會自動處理查價流程`n`n"
    PriceKeys .= "💡 指定搭配使用：`n"
    PriceKeys .= "   • rchin-poe-trade 查價工具`n"
    
    熱鍵列表GUI.Add("Text", "x475 y140 w385 h280 c0x2C3E50", PriceKeys)
    
    ; 交易流程圖
    熱鍵列表GUI.SetFont("s11 Bold", "Microsoft YaHei UI")
    熱鍵列表GUI.Add("Text", "x60 y450 w780 h25 c0xE74C3C", "📋 標準交易流程示意")
    熱鍵列表GUI.SetFont("s10", "Microsoft YaHei UI")
    熱鍵列表GUI.Add("Text", "x65 y480 w775 h60 c0x8E44AD", "[End] 申請組隊 → 等待對方加入 → [Home] 申請交易 → 雙方放入物品 → [PgUp] 確認物品 → [PgDn] 完成交易")
    
    ; === 第四個分頁：特殊功能 ===
    TabCtrl.UseTab(4)
    
    熱鍵列表GUI.SetFont("s16 Bold", "Microsoft YaHei UI")
    熱鍵列表GUI.Add("Text", "x40 y50 w800 h30 Center c0x2C3E50", "🌟 特殊功能與進階設定")
    熱鍵列表GUI.Add("Text", "x40 y85 w800 h2 Background0x8E44AD")
    
    ; 循環技能系統
    熱鍵列表GUI.SetFont("s12 Bold", "Microsoft YaHei UI")
    熱鍵列表GUI.Add("Text", "x60 y110 w390 h25 c0x8E44AD", "⚔️ 循環技能系統")
    
    熱鍵列表GUI.SetFont("s10", "Microsoft YaHei UI")
    SkillSystem := "🔄 [Insert] 開啟/關閉循環技能`n"
    SkillSystem .= "支援功能：`n"
    SkillSystem .= "• 自訂 5 個技能位置 (Q/W/E/R/T)`n"
    SkillSystem .= "• 設定各技能的釋放間隔時間`n"
    SkillSystem .= "• 個別開關特定技能位置`n"
    SkillSystem .= "• 即時調整技能順序與時間`n`n"
    SkillSystem .= "設定方式：`n"
    SkillSystem .= "透過 Win+Z 主選單 → 循環技能設置`n`n"
    SkillSystem .= "使用場景：`n"
    SkillSystem .= "• 自動刷怪時的技能循環`n"
    SkillSystem .= "• 維持 BUFF 狀態`n"
    SkillSystem .= "• 提升刷圖效率"
    
    熱鍵列表GUI.Add("Text", "x65 y140 w385 h280 c0x2C3E50", SkillSystem)
    
    ; 滑鼠與座標功能
    熱鍵列表GUI.SetFont("s12 Bold", "Microsoft YaHei UI")
    熱鍵列表GUI.Add("Text", "x470 y110 w390 h25 c0x27AE60", "🖱️ 滑鼠與座標功能")
    
    熱鍵列表GUI.SetFont("s10", "Microsoft YaHei UI")
    MouseSystem := "🖱️ 滑鼠連點功能：`n"
    MouseSystem .= "• [滾輪下壓] 連點模式`n"
    MouseSystem .= "• 可調整連點速度與模式`n"
    MouseSystem .= "• 透過 Win+Z 選單進行設定`n`n"
    MouseSystem .= "📍 座標設定系統：`n"
    MouseSystem .= "• [Win+C] 通用座標抓取工具`n"
    MouseSystem .= "• 支援 1-9 和 T 的快速設定`n"
    MouseSystem .= "• 十字準心輔助定位`n"
    MouseSystem .= "• 即時座標預覽與調整`n`n"
    MouseSystem .= "🎯 智能拾取：`n"
    MouseSystem .= "• [F8] 開啟智能拾取`n"
    MouseSystem .= "• [Shift+F8] 拾取設定介面`n"
    
    熱鍵列表GUI.Add("Text", "x475 y140 w385 h300 c0x2C3E50", MouseSystem)
    
    ; 系統維護功能
    熱鍵列表GUI.SetFont("s11 Bold", "Microsoft YaHei UI")
    熱鍵列表GUI.Add("Text", "x60 y450 w780 h25 c0xE74C3C", "🔧 系統維護與故障排除")
    熱鍵列表GUI.SetFont("s10", "Microsoft YaHei UI")
    MaintenanceInfo := "• [F11] 重新載入腳本：解決功能異常或更新設定`n• [Ctrl+Shift+F12] 強制釋放按鍵：解決按鍵卡住問題`n• [F9] 暫停工具：臨時關閉所有功能，回復原始鍵盤操作"
    熱鍵列表GUI.Add("Text", "x65 y480 w775 h80 c0x8E44AD", MaintenanceInfo)
    
    ; 回到主分頁
    TabCtrl.UseTab()
    
    ; 底部資訊
    熱鍵列表GUI.SetFont("s10 Bold", "Microsoft YaHei UI")
    熱鍵列表GUI.Add("Text", "x30 y675 w840 h20 Center c0x2C3E50", "📋 完整熱鍵列表 - 所有功能僅在 Path of Exile 系列遊戲視窗中運作")

    ; 計算螢幕置中位置並顯示
    螢幕寬度 := A_ScreenWidth
    螢幕高度 := A_ScreenHeight
    GUI寬度 := 900
    GUI高度 := 720
    置中X := (螢幕寬度 - GUI寬度) // 2
    置中Y := (螢幕高度 - GUI高度) // 2
    熱鍵列表GUI.Show("w" . GUI寬度 . " h" . GUI高度 . " x" . 置中X . " y" . 置中Y)
}

狀態設置說明(*) {
    ; 🔥 防止重複開啟GUI
    global 當前狀態偵測GUI
    
    ; 如果GUI已經存在，顯示提醒並返回
    if (當前狀態偵測GUI != "" && IsObject(當前狀態偵測GUI)) {
        try {
            ; 銷毀舊GUI以套用新版排版
            當前狀態偵測GUI.Destroy()
            當前狀態偵測GUI := ""
            ShowToolTip("重新建立狀態偵測面板", 1500, 1)
        } catch {
            當前狀態偵測GUI := ""
        }
    }
    
    ; 狀態偵測設置GUI
    try {
        global 狀態偵測GUI := Gui("+Resize -MinimizeBox", "💚 狀態偵測設置")
        當前狀態偵測GUI := 狀態偵測GUI
        
        ; ESC快速關閉支援
        狀態偵測GUI.OnEvent("Escape", 關閉狀態偵測GUI)
        
        ; 🔥 添加關閉事件處理
        狀態偵測GUI.OnEvent("Close", 關閉狀態偵測GUI)
        
        ; 🔥 關閉函數
        關閉狀態偵測GUI(*) {
            global 當前狀態偵測GUI
            狀態偵測GUI.Destroy()
            當前狀態偵測GUI := ""
        }
    狀態偵測GUI.BackColor := "0xF0F8FF"
    狀態偵測GUI.MarginX := 18
    狀態偵測GUI.MarginY := 20
    狀態偵測GUI.SetFont("s13 Bold", "Microsoft JhengHei")
        
    狀態偵測GUI.Add("Text", "w820 Center cNavy", "智能狀態偵測系統 - 完整版")
    狀態偵測GUI.SetFont("s11", "Microsoft JhengHei")
    狀態偵測GUI.Add("Text", "w820 Center cGray", "自動監控血量、魔力、護盾變化，智能觸發藥劑使用 | 支援顏色偵測與座標記錄")
        
        ; 第一行：主要偵測功能
        狀態偵測GUI.SetFont("s12", "Microsoft JhengHei")
    狀態偵測GUI.Add("CheckBox", "x15 y100 w200 vCheckBloodDrink", "✅ 開啟偵測血條喝水")
    狀態偵測GUI.Add("CheckBox", "x230 y100 w200 vCheckBloodReturn", "🏠 開啟偵測血條返角")
    狀態偵測GUI.Add("CheckBox", "x450 y100 w200 vCheckManaDrink", "🔮 開啟偵測魔球池")
        
        ; 第二行：進階偵測功能  
        狀態偵測GUI.Add("CheckBox", "x15 y130 w200 vCheckBloodPierce", "⚡ 開啟偵測混傷穿透")
        狀態偵測GUI.Add("CheckBox", "x230 y130 w200 vCheckPierceReturn", "🔄 開啟混傷返角偵測")
        狀態偵測GUI.Add("CheckBox", "x450 y130 w180 vCheckBloodPool", "🩸 開啟偵測血球池")
        
        ; 藥劑設定區域
        狀態偵測GUI.Add("Text", "x15 y170 w750 h2 Background4169E1")
        狀態偵測GUI.SetFont("s12 Bold", "Microsoft JhengHei")
        狀態偵測GUI.Add("Text", "x15 y180 w200 cBlue", "藥劑按鍵設定")
        
        狀態偵測GUI.SetFont("s11", "Microsoft JhengHei")
    ; 藥劑按鍵設定
    狀態偵測GUI.Add("Text", "x18 y205 w140", "血條藥劑按鍵:")
    PotionKey1 := 狀態偵測GUI.Add("Edit", "x170 y203 w90 h26 vPotionKey1", "1")

    狀態偵測GUI.Add("Text", "x280 y205 w140", "魔球藥劑按鍵:")
    PotionKey2 := 狀態偵測GUI.Add("Edit", "x420 y203 w90 h26 vPotionKey2", "2")

    狀態偵測GUI.Add("Text", "x530 y205 w140", "穿透藥劑按鍵:")
    PotionKey3 := 狀態偵測GUI.Add("Edit", "x680 y203 w90 h26 vPotionKey3", "3")

    狀態偵測GUI.Add("Text", "x18 y240 w140", "血球藥劑按鍵:")
    PotionKey4 := 狀態偵測GUI.Add("Edit", "x170 y233 w90 h26 vPotionKey4", "4")
    ; 綁定 Change 事件以過濾只保留單字/數字
    PotionKey1.OnEvent("Change", (*) => PotionKey1.Text := FilterValidChars(PotionKey1.Text))
    PotionKey2.OnEvent("Change", (*) => PotionKey2.Text := FilterValidChars(PotionKey2.Text))
    PotionKey3.OnEvent("Change", (*) => PotionKey3.Text := FilterValidChars(PotionKey3.Text))
    PotionKey4.OnEvent("Change", (*) => PotionKey4.Text := FilterValidChars(PotionKey4.Text))
        
        狀態偵測GUI.Add("Text", "x280 y240 w120", "喝水間隔(毫秒):")
    DetectIntervalCB := 狀態偵測GUI.Add("ComboBox", "x420 y233 w92 vDetectInterval")
        DetectIntervalCB.Add(["100", "300", "500", "800", "1000", "2000", "3000"])
        DetectIntervalCB.Choose(5)  ; 預設1000ms
        
        狀態偵測GUI.Add("Text", "x530 y235 w80", "喝水提示:")
        DrinkNotifyCB := 狀態偵測GUI.Add("ComboBox", "x680 y233 w92 vDrinkNotify")
        DrinkNotifyCB.Add(["開啟", "關閉"])
        DrinkNotifyCB.Choose(1)  ; 預設選擇 "開啟"
        
        ; 🎯 顏色容錯設定區域
    狀態偵測GUI.Add("Text", "x18 y265 w140", "顏色容錯值:")
    ColorToleranceCB := 狀態偵測GUI.Add("ComboBox", "x170 y263 w92 vColorTolerance")
        ColorToleranceCB.Add(["0", "5", "10", "15", "20", "25"])
        ColorToleranceCB.Choose(1)  ; 預設選擇 0 (精確比對)
        狀態偵測GUI.Add("Text", "x280 y266 w500 cGray", "💡 調整範圍: 0-25  |  0 = 精確比對，數值越大容錯越高但可能誤觸")

        ; 座標設定區域
        狀態偵測GUI.Add("Text", "x15 y295 w750 h2 Background4169E1")
        狀態偵測GUI.SetFont("s12 Bold", "Microsoft JhengHei")
        狀態偵測GUI.Add("Text", "x15 y305 w300 cBlue", "座標與顏色偵測設定")
        
        狀態偵測GUI.SetFont("s11", "Microsoft JhengHei")
    狀態偵測GUI.Add("Text", "x18 y330 w780 cRed", "使用方法: 滑鼠指向偵測位置按 [Win+C] 抓取→輸入代號 1-9 | 準心顯示抓取位置")
    狀態偵測GUI.Add("Text", "x18 y352 w780 cBlue", "座標越接近滿血=提早觸發 | 位置不對請按ESC關閉面板重新定位")
        
        ; 座標顯示區域
        狀態偵測GUI.Add("Text", "x15 y375 w180", "🌍 場景偵測點 (代號1):")
    狀態偵測GUI.Add("Text", "x200 y375 w260 vCoord1", "載入中...")
        
        狀態偵測GUI.Add("Text", "x15 y400 w180", "💬 對話框1偵測 (代號2):")
    狀態偵測GUI.Add("Text", "x200 y400 w260 vCoord2", "載入中...")
        
        狀態偵測GUI.Add("Text", "x15 y425 w180", "� 對話框(2)偵測 (代號3):")
    狀態偵測GUI.Add("Text", "x200 y425 w260 vCoord3", "載入中...")
        
        狀態偵測GUI.Add("Text", "x15 y450 w180", "🩸 血球池偵測點 (代號4):")
    狀態偵測GUI.Add("Text", "x200 y450 w260 vCoord4", "載入中...")
        
        狀態偵測GUI.Add("Text", "x15 y475 w180", "🔮 魔球偵測點 (代號5):")
    狀態偵測GUI.Add("Text", "x200 y475 w260 vCoord5", "載入中...")
        
        狀態偵測GUI.Add("Text", "x15 y500 w180", "🔴 血條喝水點 (代號6):")
    狀態偵測GUI.Add("Text", "x200 y500 w260 vCoord6", "載入中...")
        
        狀態偵測GUI.Add("Text", "x390 y375 w180", "🏠 血條返角點 (代號7):")
    狀態偵測GUI.Add("Text", "x575 y375 w260 vCoord7", "載入中...")
        
        狀態偵測GUI.Add("Text", "x390 y400 w180", "⚡ 血條穿透點 (代號8):")
    狀態偵測GUI.Add("Text", "x575 y400 w260 vCoord8", "載入中...")
        
        狀態偵測GUI.Add("Text", "x390 y425 w180", "🔄 穿透返角點 (代號9):")
    狀態偵測GUI.Add("Text", "x575 y425 w260 vCoord9", "載入中...")
        
        ; 🔥 新增重新整理按鈕
    狀態偵測GUI.Add("Button", "x450 y450 w150 h28", "🔄 重新整理狀態").OnEvent("Click", (*) => 更新座標顯示狀態(狀態偵測GUI))
        
        ; F10 高級功能說明區域
    狀態偵測GUI.Add("Text", "x18 y525 w750 h2 Background0xFF4500")
        狀態偵測GUI.SetFont("s13 Bold", "Microsoft JhengHei")
    狀態偵測GUI.Add("Text", "x18 y535 w380 cRed", "F10 高級功能控制台")
        
        狀態偵測GUI.SetFont("s11", "Microsoft JhengHei")
        狀態偵測GUI.Add("Text", "x18 y560 w750 cBlue", 
            "完成上述設置後，即可使用 F10 功能鍵快速控制所有偵測功能：")

        狀態偵測GUI.Add("Text", "x18 y580 w750 cBlue", 
            "🔴 F10 按下: 🔴關閉狀態 → 🟡基礎模式 (血球+魔球+場景)")
        狀態偵測GUI.Add("Text", "x18 y600 w750 cBlue", 
            "🟡 F10 按下: 🟡基礎狀態 → 🟢完整模式 (基礎+血條+混傷穿透)")
        狀態偵測GUI.Add("Text", "x18 y620 w750 cBlue", 
            "🟢 F10 按下: 🟢完整狀態 → 🔴關閉模式 (停止所有偵測)")
        
        狀態偵測GUI.Add("Text", "x18 y645 w750 cGreen", 
            "⚠️ 重要: 場景偵測點(1)、對話框1偵測(2)、對話框2偵測(3)是必須設置，其他為選用功能")
        狀態偵測GUI.Add("Text", "x18 y665 w750 cPurple", 
            "💡 提示: 完成設置後使用F10可快速控制所有偵測功能")
        
        ; 按鈕區域
        狀態偵測GUI.SetFont("s12 Bold", "Microsoft JhengHei")
    狀態偵測GUI.Add("Button", "x18 y700 w160 h36", "儲存設定").OnEvent("Click", (*) => 儲存狀態偵測設置())
    狀態偵測GUI.Add("Button", "x200 y700 w120 h36", "取消").OnEvent("Click", 關閉狀態偵測GUI)
    狀態偵測GUI.Add("Button", "x340 y700 w160 h36", "載入設定").OnEvent("Click", (*) => 載入偵測設定())
    狀態偵測GUI.Add("Button", "x520 y700 w160 h36", "抓取座標教學").OnEvent("Click", (*) => 座標抓取教學())

        ; 狀態說明
        狀態偵測GUI.SetFont("s10", "Microsoft JhengHei")
    狀態偵測GUI.Add("Text", "x18 y745 w800 cGray", "💡 小技巧: 完成設置後使用 F10 可快速控制所有偵測功能 | 製作 By Sid")
        
        ; 載入已儲存的設定到GUI
        更新狀態偵測GUI顯示()
        
        ; 顯示GUI (調整大小)
    狀態偵測GUI.Show("w800 h800")
        ; 顯示後再強制刷新資料與座標顯示，避免文字覆蓋或未更新
        更新狀態偵測GUI顯示()
        更新座標顯示狀態(狀態偵測GUI)
        ; ESC快速關閉支援
        狀態偵測GUI.OnEvent("Escape", (*) => 狀態偵測GUI.Destroy())
        ShowToolTip("偵測喝水設置GUI已開啟 - 包含F10功能說明", 2000)
        
    } catch Error as err {
        SmartMsgBox("創建狀態偵測GUI時發生錯誤:`n" . err.message, "錯誤", 0x10)
    }
}

技能設置說明(*) {
    Show_技能連段設置GUI()
}

循環設置說明(*) {
    Show_循環技能設置GUI()
}

倉庫設置說明(*) {
    ToolTip("功能開發中...`n將提供倉庫快速搜尋功能")
    SetTimer(() => ToolTip(), -3000)
}

連點設置說明(*) {
    Show_MouseClickGui()
}

地雷設置說明(*) {
    Show_地雷設置GUI()
}

; ========================== 循環技能系統 ==========================

; Insert 循環技能熱鍵處理
Insert_循環技能(*) {
    global StopUser, 循環技能1, 循環技能2, 循環技能3, 循環技能4, 循環技能5
    global 循環技能時間1, 循環技能時間2, 循環技能時間3, 循環技能時間4, 循環技能時間5
    
    ; 切換循環技能狀態
    if (StopUser = 0) {
        StopUser := 1
        ShowToolTip("✅ 循環技能已開啟", 2000, 1)
    } else {
        StopUser := 0
        ShowToolTip("❌ 循環技能已關閉", 2000, 1)
    }
    
    ; 檢查是否至少有一個技能啟用 (時間不為OFF)
    hasActiveSkill := false
    if (循環技能時間1 != "OFF" && IsNumber(循環技能時間1)) hasActiveSkill := true
    if (循環技能時間2 != "OFF" && IsNumber(循環技能時間2)) hasActiveSkill := true
    if (循環技能時間3 != "OFF" && IsNumber(循環技能時間3)) hasActiveSkill := true
    if (循環技能時間4 != "OFF" && IsNumber(循環技能時間4)) hasActiveSkill := true
    if (循環技能時間5 != "OFF" && IsNumber(循環技能時間5)) hasActiveSkill := true
    
    if (!hasActiveSkill && StopUser = 1) {
        StopUser := 0
        SmartMsgBox("⚠️ 所有技能循環時間都設為OFF!`n請先設定至少一個技能的循環時間。", "設置提醒", 0x30)
        Show_循環技能設置GUI()
        return
    }
    
    if (StopUser = 1) {
        ; 開啟循環技能
        啟動循環技能()
    } else {
        ; 關閉循環技能
        關閉循環技能()
    }
}

; 啟動循環技能
啟動循環技能() {
    global 循環技能1, 循環技能2, 循環技能3, 循環技能4, 循環技能5
    global 循環技能時間1, 循環技能時間2, 循環技能時間3, 循環技能時間4, 循環技能時間5
    
    ; 循環保險，先關閉避免運作異常
    SetTimer(循環技能1_執行, 0)
    SetTimer(循環技能2_執行, 0)
    SetTimer(循環技能3_執行, 0)
    SetTimer(循環技能4_執行, 0)
    SetTimer(循環技能5_執行, 0)
    
    ; 立即執行一次
    循環技能1_執行()
    循環技能2_執行()
    循環技能3_執行()
    循環技能4_執行()
    循環技能5_執行()
    
    ; 設定循環定時器並記錄啟動狀態
    activeTimers := []
    if (循環技能時間1 != "OFF" && IsNumber(循環技能時間1)) {
        SetTimer(循環技能1_執行, 循環技能時間1)
        activeTimers.Push("技能1(" . 循環技能1 . ":" . 循環技能時間1 . "ms)")
    }
    if (循環技能時間2 != "OFF" && IsNumber(循環技能時間2)) {
        SetTimer(循環技能2_執行, 循環技能時間2)
        activeTimers.Push("技能2(" . 循環技能2 . ":" . 循環技能時間2 . "ms)")
    }
    if (循環技能時間3 != "OFF" && IsNumber(循環技能時間3)) {
        SetTimer(循環技能3_執行, 循環技能時間3)
        activeTimers.Push("技能3(" . 循環技能3 . ":" . 循環技能時間3 . "ms)")
    }
    if (循環技能時間4 != "OFF" && IsNumber(循環技能時間4)) {
        SetTimer(循環技能4_執行, 循環技能時間4)
        activeTimers.Push("技能4(" . 循環技能4 . ":" . 循環技能時間4 . "ms)")
    }
    if (循環技能時間5 != "OFF" && IsNumber(循環技能時間5)) {
        SetTimer(循環技能5_執行, 循環技能時間5)
        activeTimers.Push("技能5(" . 循環技能5 . ":" . 循環技能時間5 . "ms)")
    }
    
    ; 顯示啟動狀態
    if (activeTimers.Length > 0) {
        statusMsg := "🔄 已啟動 " . activeTimers.Length . " 個循環技能:`n" . 
                    activeTimers[1] . (activeTimers.Length > 1 ? "`n" . activeTimers[2] : "") .
                    (activeTimers.Length > 2 ? "`n" . activeTimers[3] : "") .
                    (activeTimers.Length > 3 ? "`n" . activeTimers[4] : "") .
                    (activeTimers.Length > 4 ? "`n" . activeTimers[5] : "")
        ShowToolTip(statusMsg, 4000, 1)
    }
}

; 關閉循環技能
關閉循環技能() {
    SetTimer(循環技能1_執行, 0)
    SetTimer(循環技能2_執行, 0)
    SetTimer(循環技能3_執行, 0)
    SetTimer(循環技能4_執行, 0)
    SetTimer(循環技能5_執行, 0)
}

; 循環技能執行函數
循環技能1_執行() {
    global 循環技能1, 循環技能時間1, Toolbutton
    
    if (!WinActive("Path of Exile") && !WinActive("Path of Exile 2")) {
        return
    }
    
    if (Toolbutton = 1) {  ; 文字模式不執行
        return
    }
    
    if (循環技能時間1 = "OFF") {
        return
    }
    
    ; 檢查修飾鍵狀態
    if (GetKeyState("Ctrl", "P") || GetKeyState("Shift", "P")) {
        return
    }
    
    if (循環技能1 != "" && 循環技能1 != "OFF") {
        ; 處理不同類型的按鍵
        if (循環技能1 = "LButton") {
            Click("Left")
        } else if (循環技能1 = "RButton") {
            Click("Right")
        } else if (循環技能1 = "MButton") {
            Click("Middle")
        } else {
            Send("{" . 循環技能1 . "}")
        }
        Send("{BS}")  ; 防止聊天輸入
    }
}

循環技能2_執行() {
    global 循環技能2, 循環技能時間2, Toolbutton
    
    if (!WinActive("Path of Exile") && !WinActive("Path of Exile 2")) {
        return
    }
    
    if (Toolbutton = 1) {
        return
    }
    
    if (循環技能時間2 = "OFF") {
        return
    }
    
    if (GetKeyState("Ctrl", "P") || GetKeyState("Shift", "P")) {
        return
    }
    
    if (循環技能2 != "" && 循環技能2 != "OFF") {
        ; 處理不同類型的按鍵
        if (循環技能2 = "LButton") {
            Click("Left")
        } else if (循環技能2 = "RButton") {
            Click("Right")
        } else if (循環技能2 = "MButton") {
            Click("Middle")
        } else {
            Send("{" . 循環技能2 . "}")
        }
        Send("{BS}")
    }
}

循環技能3_執行() {
    global 循環技能3, 循環技能時間3, Toolbutton
    
    if (!WinActive("Path of Exile") && !WinActive("Path of Exile 2")) {
        return
    }
    
    if (Toolbutton = 1) {
        return
    }
    
    if (循環技能時間3 = "OFF") {
        return
    }
    
    if (GetKeyState("Ctrl", "P") || GetKeyState("Shift", "P")) {
        return
    }
    
    if (循環技能3 != "" && 循環技能3 != "OFF") {
        ; 處理不同類型的按鍵
        if (循環技能3 = "LButton") {
            Click("Left")
        } else if (循環技能3 = "RButton") {
            Click("Right")
        } else if (循環技能3 = "MButton") {
            Click("Middle")
        } else {
            Send("{" . 循環技能3 . "}")
        }
        Send("{BS}")
    }
}

循環技能4_執行() {
    global 循環技能4, 循環技能時間4, Toolbutton
    
    if (!WinActive("Path of Exile") && !WinActive("Path of Exile 2")) {
        return
    }
    
    if (Toolbutton = 1) {
        return
    }
    
    if (循環技能時間4 = "OFF") {
        return
    }
    
    if (GetKeyState("Ctrl", "P") || GetKeyState("Shift", "P")) {
        return
    }
    
    if (循環技能4 != "" && 循環技能4 != "OFF") {
        ; 處理不同類型的按鍵
        if (循環技能4 = "LButton") {
            Click("Left")
        } else if (循環技能4 = "RButton") {
            Click("Right")
        } else if (循環技能4 = "MButton") {
            Click("Middle")
        } else {
            Send("{" . 循環技能4 . "}")
        }
        Send("{BS}")
    }
}

循環技能5_執行() {
    global 循環技能5, 循環技能時間5, Toolbutton
    
    if (!WinActive("Path of Exile") && !WinActive("Path of Exile 2")) {
        return
    }
    
    if (Toolbutton = 1) {
        return
    }
    
    if (循環技能時間5 = "OFF") {
        return
    }
    
    if (GetKeyState("Ctrl", "P") || GetKeyState("Shift", "P")) {
        return
    }
    
    if (循環技能5 != "" && 循環技能5 != "OFF") {
        ; 處理不同類型的按鍵
        if (循環技能5 = "LButton") {
            Click("Left")
        } else if (循環技能5 = "RButton") {
            Click("Right")
        } else if (循環技能5 = "MButton") {
            Click("Middle")
        } else {
            Send("{" . 循環技能5 . "}")
        }
        Send("{BS}")
    }
}

; 顯示循環技能設置GUI - 現代化版本
Show_循環技能設置GUI() {
    global 循環技能1, 循環技能2, 循環技能3, 循環技能4, 循環技能5
    global 循環技能時間1, 循環技能時間2, 循環技能時間3, 循環技能時間4, 循環技能時間5, StopUser
    
    ; 讀取當前設定
    讀取循環技能設置()
    
    ; 創建現代化循環技能設置GUI
    循環設置GUI := Gui("+AlwaysOnTop -MinimizeBox -MaximizeBox", "🔄 循環技能設置")
    循環設置GUI.BackColor := "0x2D2D30"
    循環設置GUI.SetFont("s11", "Microsoft YaHei UI")
    循環設置GUI.MarginX := 25
    循環設置GUI.MarginY := 20
    
    ; 標題
    title := 循環設置GUI.Add("Text", "x25 y20 w450 h35 Center c0xFFFFFF", "🔄 循環技能設置控制台")
    title.SetFont("s14 Bold", "Microsoft YaHei UI")
    
    ; 說明文字
    循環設置GUI.Add("Text", "x25 y60 w450 h25 c0xC0C0C0", "設定按鍵與多少毫秒使用一次 (OFF: 關閉)")
    循環設置GUI.Add("Text", "x25 y455 w450 h25 c0xFFFF00", "💡 儲存完成後，使用 Insert 鍵開啟循環")
    
    ; 創建豐富的按鍵選項列表
    keyOptions := ["OFF", 
                   "A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M", 
                   "N", "O", "P", "Q", "R", "S", "T", "U", "V", "W", "X", "Y", "Z",
                   "1", "2", "3", "4", "5",
                   "LButton", "RButton", "MButton"]
    
    timeOptions := ["OFF", "500", "1000", "1500", "2000", "2500", "3000", "4000", "5000", "6000", "7000", "8000", "9000", "10000"]
    
    ; 技能1設定 - 加大間距和控件尺寸
    循環設置GUI.Add("Text", "x25 y95 w65 h25 c0x00FFFF", "技能1:")
    skill1Combo := 循環設置GUI.Add("ComboBox", "x95 y95 w110 h28 R10", keyOptions)
    skill1Combo.Text := 循環技能1
    skill1Combo.SetFont("s11")
    
    循環設置GUI.Add("Text", "x220 y95 w45 h25 c0xC0C0C0", "間隔:")
    time1Combo := 循環設置GUI.Add("ComboBox", "x270 y95 w100 h28 R10", timeOptions)
    time1Combo.Text := 循環技能時間1
    time1Combo.SetFont("s11")
    
    循環設置GUI.Add("Text", "x380 y95 w35 h25 c0x808080", "ms")
    
    ; 技能2設定
    循環設置GUI.Add("Text", "x25 y135 w65 h25 c0x00FFFF", "技能2:")
    skill2Combo := 循環設置GUI.Add("ComboBox", "x95 y135 w110 h28 R10", keyOptions)
    skill2Combo.Text := 循環技能2
    skill2Combo.SetFont("s11")
    
    循環設置GUI.Add("Text", "x220 y135 w45 h25 c0xC0C0C0", "間隔:")
    time2Combo := 循環設置GUI.Add("ComboBox", "x270 y135 w100 h28 R10", timeOptions)
    time2Combo.Text := 循環技能時間2
    time2Combo.SetFont("s11")
    
    循環設置GUI.Add("Text", "x380 y135 w35 h25 c0x808080", "ms")
    
    ; 技能3設定
    循環設置GUI.Add("Text", "x25 y175 w65 h25 c0x00FFFF", "技能3:")
    skill3Combo := 循環設置GUI.Add("ComboBox", "x95 y175 w110 h28 R10", keyOptions)
    skill3Combo.Text := 循環技能3
    skill3Combo.SetFont("s11")
    
    循環設置GUI.Add("Text", "x220 y175 w45 h25 c0xC0C0C0", "間隔:")
    time3Combo := 循環設置GUI.Add("ComboBox", "x270 y175 w100 h28 R10", timeOptions)
    time3Combo.Text := 循環技能時間3
    time3Combo.SetFont("s11")
    
    循環設置GUI.Add("Text", "x380 y175 w35 h25 c0x808080", "ms")
    
    ; 技能4設定
    循環設置GUI.Add("Text", "x25 y215 w65 h25 c0x00FFFF", "技能4:")
    skill4Combo := 循環設置GUI.Add("ComboBox", "x95 y215 w110 h28 R10", keyOptions)
    skill4Combo.Text := 循環技能4
    skill4Combo.SetFont("s11")
    
    循環設置GUI.Add("Text", "x220 y215 w45 h25 c0xC0C0C0", "間隔:")
    time4Combo := 循環設置GUI.Add("ComboBox", "x270 y215 w100 h28 R10", timeOptions)
    time4Combo.Text := 循環技能時間4
    time4Combo.SetFont("s11")
    
    循環設置GUI.Add("Text", "x380 y215 w35 h25 c0x808080", "ms")
    
    ; 技能5設定
    循環設置GUI.Add("Text", "x25 y255 w65 h25 c0x00FFFF", "技能5:")
    skill5Combo := 循環設置GUI.Add("ComboBox", "x95 y255 w110 h28 R10", keyOptions)
    skill5Combo.Text := 循環技能5
    skill5Combo.SetFont("s11")
    
    循環設置GUI.Add("Text", "x220 y255 w45 h25 c0xC0C0C0", "間隔:")
    time5Combo := 循環設置GUI.Add("ComboBox", "x270 y255 w100 h28 R10", timeOptions)
    time5Combo.Text := 循環技能時間5
    time5Combo.SetFont("s11")
    
    循環設置GUI.Add("Text", "x380 y255 w35 h25 c0x808080", "ms")
    
    ; 說明區域 - 調整位置和字體
    noteText := 循環設置GUI.Add("Text", "x25 y295 w450 h80 c0xFFA500 BackgroundTrans", 
        "⚠️ 注意事項:`n" .
        "• 滑鼠按鍵: LButton(左鍵), RButton(右鍵), MButton(中鍵)`n" .
        "• 數字鍵: 1-5 為主鍵盤數字鍵 (非小鍵盤)`n" .
        "• 僅在遊戲視窗活躍時才會發送按鍵，避免誤觸")
    noteText.SetFont("s10")
    
    ; 按鈕區 - 增大按鈕尺寸和間距
    saveBtn := 循環設置GUI.Add("Button", "x120 y485 w110 h35", "✅ 儲存設定")
    saveBtn.SetFont("s11")
    cancelBtn := 循環設置GUI.Add("Button", "x250 y485 w110 h35", "❌ 取消")
    cancelBtn.SetFont("s11")
    
    ; 儲存按鈕事件處理函數
    SaveSettings() {
        ; 獲取設定值
        循環技能1 := skill1Combo.Text
        循環技能2 := skill2Combo.Text
        循環技能3 := skill3Combo.Text
        循環技能4 := skill4Combo.Text
        循環技能5 := skill5Combo.Text
        循環技能時間1 := time1Combo.Text
        循環技能時間2 := time2Combo.Text
        循環技能時間3 := time3Combo.Text
        循環技能時間4 := time4Combo.Text
        循環技能時間5 := time5Combo.Text
        
        ; 儲存設定
        儲存循環技能設置()
        
        ; 如果循環技能正在運行，重新啟動
        if (StopUser = 1) {
            StopUser := 0
            關閉循環技能()
            ShowToolTip("⚠️ 設定已更新，已自動關閉循環功能`n請重新按 Insert 鍵啟動", 3000, 1)
        } else {
            ShowToolTip("✅ 循環技能設定已儲存", 2000, 1)
        }
        
        循環設置GUI.Destroy()
    }
    
    ; 綁定事件
    saveBtn.OnEvent("Click", (*) => SaveSettings())
    cancelBtn.OnEvent("Click", (*) => 循環設置GUI.Destroy())
    
    ; 關閉事件
    循環設置GUI.OnEvent("Close", (*) => 循環設置GUI.Destroy())
    循環設置GUI.OnEvent("Escape", (*) => 循環設置GUI.Destroy())
    
    ; 顯示GUI - 調整窗口尺寸
    循環設置GUI.Show("w500 h540")
}

; 儲存循環技能設置
儲存循環技能設置() {
    global 循環技能1, 循環技能2, 循環技能3, 循環技能4, 循環技能5
    global 循環技能時間1, 循環技能時間2, 循環技能時間3, 循環技能時間4, 循環技能時間5
    global CONFIG_FILE
    
    try {
        ; 統一使用單一配置
        IniWrite(循環技能1, CONFIG_FILE, "循環技能", "循環技能1")
        IniWrite(循環技能2, CONFIG_FILE, "循環技能", "循環技能2")
        IniWrite(循環技能3, CONFIG_FILE, "循環技能", "循環技能3")
        IniWrite(循環技能4, CONFIG_FILE, "循環技能", "循環技能4")
        IniWrite(循環技能5, CONFIG_FILE, "循環技能", "循環技能5")
        IniWrite(循環技能時間1, CONFIG_FILE, "循環技能", "循環技能時間1")
        IniWrite(循環技能時間2, CONFIG_FILE, "循環技能", "循環技能時間2")
        IniWrite(循環技能時間3, CONFIG_FILE, "循環技能", "循環技能時間3")
        IniWrite(循環技能時間4, CONFIG_FILE, "循環技能", "循環技能時間4")
        IniWrite(循環技能時間5, CONFIG_FILE, "循環技能", "循環技能時間5")
    } catch Error as err {
        ShowToolTip("❌ 設定儲存失敗: " . err.message, 3000, 1)
    }
}

; 讀取循環技能設置
讀取循環技能設置() {
    global 循環技能1, 循環技能2, 循環技能3, 循環技能4, 循環技能5
    global 循環技能時間1, 循環技能時間2, 循環技能時間3, 循環技能時間4, 循環技能時間5
    global CONFIG_FILE
    
    try {
        ; 統一使用單一配置
        循環技能1 := IniRead(CONFIG_FILE, "循環技能", "循環技能1", "Q")
        循環技能2 := IniRead(CONFIG_FILE, "循環技能", "循環技能2", "W")
        循環技能3 := IniRead(CONFIG_FILE, "循環技能", "循環技能3", "E")
        循環技能4 := IniRead(CONFIG_FILE, "循環技能", "循環技能4", "R")
        循環技能5 := IniRead(CONFIG_FILE, "循環技能", "循環技能5", "T")
        循環技能時間1 := IniRead(CONFIG_FILE, "循環技能", "循環技能時間1", "OFF")
        循環技能時間2 := IniRead(CONFIG_FILE, "循環技能", "循環技能時間2", "OFF")
        循環技能時間3 := IniRead(CONFIG_FILE, "循環技能", "循環技能時間3", "OFF")
        循環技能時間4 := IniRead(CONFIG_FILE, "循環技能", "循環技能時間4", "OFF")
        循環技能時間5 := IniRead(CONFIG_FILE, "循環技能", "循環技能時間5", "OFF")
    } catch Error as err {
        ShowToolTip("⚠️ 讀取循環技能設定失敗: " . err.message, 3000, 1)
    }
}

; ======================================================================================================
; 技能連段功能
; ======================================================================================================

; 技能連段核心執行函數
執行技能連段(觸發按鍵) {
    global 技能連段狀態, 技能連段序列, 技能連段延遲, 高級功能狀態
    
    ; 檢查功能是否啟用
    if (技能連段狀態 != "開啟" || 高級功能狀態 < 1) {
        return
    }
    
    ; 檢查是否有該按鍵的連段設定
    if (!技能連段序列.Has(觸發按鍵)) {
        return
    }
    
    try {
        ; 獲取連段序列
        序列 := 技能連段序列[觸發按鍵]
        延遲設定 := 技能連段延遲[觸發按鍵]
        
        ; 顯示連段提示
        ShowToolTip("⚔️ 技能連段: " . 觸發按鍵 . " → " . StrReplace(序列, "|", " → "), 2000, 3)
        
        ; 分割序列並執行
        技能列表 := StrSplit(序列, "|")
        延遲列表 := StrSplit(延遲設定, "|")
        
        ; 執行連段
        for index, 技能 in 技能列表 {
            if (技能 == "OFF" || 技能 == "") {
                continue
            }
            
            ; 獲取對應延遲，如果沒有則使用預設100ms
            延遲時間 := (index <= 延遲列表.Length) ? Integer(延遲列表[index]) : 100
            
            ; 延遲後按下技能
            Sleep(延遲時間)
            Send("{" . 技能 . " down}")
            Sleep(10)  ; 短暫按住
            Send("{" . 技能 . " up}")
        }
        
    } catch Error as err {
        ShowToolTip("❌ 技能連段執行錯誤: " . err.message, 3000, 1)
    }
}

; 顯示技能連段設置GUI
Show_技能連段設置GUI() {
    global 技能連段狀態, 技能連段序列, 技能連段延遲, 技能連段GUI
    
    try {
        ; 創建現代化技能連段設置GUI
        技能連段GUI := Gui("+AlwaysOnTop -MinimizeBox -MaximizeBox +Resize", "⚔️ 技能連段設置中心")
        技能連段GUI.BackColor := "0x2C2C2C"  ; 深灰色背景
        技能連段GUI.SetFont("s12 Bold", "Microsoft YaHei UI")
        
        ; === 標題區域 ===
        技能連段GUI.SetFont("s16 Bold", "Microsoft YaHei UI")
        技能連段GUI.Add("Text", "x20 y15 w600 h35 Center c0x00FFFF BackgroundTrans", "⚔️ 技能連段系統控制台 ⚔️")
        
        ; === 主開關區域 ===
        技能連段GUI.SetFont("s11 Bold", "Microsoft YaHei UI") 
        技能連段GUI.Add("Text", "x30 y65 w120 h25 c0xFFFFFF BackgroundTrans", "🎯 連段狀態:")
        
        狀態選項 := ["關閉", "開啟"]
        當前狀態索引 := (技能連段狀態 == "開啟") ? 2 : 1
        狀態下拉 := 技能連段GUI.Add("DropDownList", "x160 y62 w100 h25 R3 Choose" . 當前狀態索引, 狀態選項)
        狀態下拉.SetFont("s10", "Microsoft YaHei UI")
        
        ; === 連段設定區域 ===
        技能連段GUI.SetFont("s12 Bold", "Microsoft YaHei UI")
        技能連段GUI.Add("Text", "x30 y105 w600 h25 c0xFFFF80 BackgroundTrans", "⚙️ 連段配置 (觸發按鍵 → 連段序列)")
        
        ; 技能按鍵選項
        技能選項 := ["OFF", "Q", "W", "E", "R", "T", "1", "2", "3", "4", "5"]
        
        ; Q技能連段設定
        技能連段GUI.SetFont("s10 Bold", "Microsoft YaHei UI")
        技能連段GUI.Add("Text", "x30 y140 w50 h25 c0x90EE90 BackgroundTrans", "🔥 Q →")
        
        ; 獲取當前Q技能的設定
        Q序列 := 技能連段序列.Has("q") ? 技能連段序列["q"] : "OFF|OFF|OFF"
        Q延遲 := 技能連段延遲.Has("q") ? 技能連段延遲["q"] : "100|150|200"
        Q技能列表 := StrSplit(Q序列, "|")
        Q延遲列表 := StrSplit(Q延遲, "|")
        
        ; Q連段序列控制項
        Q技能1 := 技能連段GUI.Add("DropDownList", "x85 y137 w60 h25 R3", 技能選項)
        Q技能1.Text := (Q技能列表.Length >= 1) ? Q技能列表[1] : "OFF"
        技能連段GUI.Add("Text", "x150 y140 w25 h25 c0xFFFFFF BackgroundTrans Center", "→")
        
        Q技能2 := 技能連段GUI.Add("DropDownList", "x175 y137 w60 h25 R3", 技能選項)
        Q技能2.Text := (Q技能列表.Length >= 2) ? Q技能列表[2] : "OFF"
        技能連段GUI.Add("Text", "x240 y140 w25 h25 c0xFFFFFF BackgroundTrans Center", "→")
        
        Q技能3 := 技能連段GUI.Add("DropDownList", "x265 y137 w60 h25 R3", 技能選項)
        Q技能3.Text := (Q技能列表.Length >= 3) ? Q技能列表[3] : "OFF"
        
        ; Q延遲設定
        技能連段GUI.Add("Text", "x340 y140 w50 h25 c0xFFD700 BackgroundTrans", "延遲:")
        Q延遲1 := 技能連段GUI.Add("Edit", "x390 y137 w40 h25 Number")
        Q延遲1.Text := (Q延遲列表.Length >= 1) ? Q延遲列表[1] : "100"
        Q延遲2 := 技能連段GUI.Add("Edit", "x435 y137 w40 h25 Number")
        Q延遲2.Text := (Q延遲列表.Length >= 2) ? Q延遲列表[2] : "150"
        Q延遲3 := 技能連段GUI.Add("Edit", "x480 y137 w40 h25 Number")
        Q延遲3.Text := (Q延遲列表.Length >= 3) ? Q延遲列表[3] : "200"
        技能連段GUI.Add("Text", "x525 y140 w30 h25 c0xC0C0C0 BackgroundTrans", "ms")
        
        ; W技能連段設定
        技能連段GUI.Add("Text", "x30 y175 w50 h25 c0x87CEEB BackgroundTrans", "❄️ W →")
        
        W序列 := 技能連段序列.Has("w") ? 技能連段序列["w"] : "OFF|OFF|OFF"
        W延遲 := 技能連段延遲.Has("w") ? 技能連段延遲["w"] : "100|150|200"
        W技能列表 := StrSplit(W序列, "|")
        W延遲列表 := StrSplit(W延遲, "|")
        
        W技能1 := 技能連段GUI.Add("DropDownList", "x85 y172 w60 h25 R3", 技能選項)
        W技能1.Text := (W技能列表.Length >= 1) ? W技能列表[1] : "OFF"
        技能連段GUI.Add("Text", "x150 y175 w25 h25 c0xFFFFFF BackgroundTrans Center", "→")
        
        W技能2 := 技能連段GUI.Add("DropDownList", "x175 y172 w60 h25 R3", 技能選項)
        W技能2.Text := (W技能列表.Length >= 2) ? W技能列表[2] : "OFF"
        技能連段GUI.Add("Text", "x240 y175 w25 h25 c0xFFFFFF BackgroundTrans Center", "→")
        
        W技能3 := 技能連段GUI.Add("DropDownList", "x265 y172 w60 h25 R3", 技能選項)
        W技能3.Text := (W技能列表.Length >= 3) ? W技能列表[3] : "OFF"
        
        技能連段GUI.Add("Text", "x340 y175 w50 h25 c0xFFD700 BackgroundTrans", "延遲:")
        W延遲1 := 技能連段GUI.Add("Edit", "x390 y172 w40 h25 Number")
        W延遲1.Text := (W延遲列表.Length >= 1) ? W延遲列表[1] : "100"
        W延遲2 := 技能連段GUI.Add("Edit", "x435 y172 w40 h25 Number")
        W延遲2.Text := (W延遲列表.Length >= 2) ? W延遲列表[2] : "150"
        W延遲3 := 技能連段GUI.Add("Edit", "x480 y172 w40 h25 Number")
        W延遲3.Text := (W延遲列表.Length >= 3) ? W延遲列表[3] : "200"
        技能連段GUI.Add("Text", "x525 y175 w30 h25 c0xC0C0C0 BackgroundTrans", "ms")
        
        ; E技能連段設定
        技能連段GUI.Add("Text", "x30 y210 w50 h25 c0xFFB6C1 BackgroundTrans", "⚡ E →")
        
        E序列 := 技能連段序列.Has("e") ? 技能連段序列["e"] : "OFF|OFF|OFF"
        E延遲 := 技能連段延遲.Has("e") ? 技能連段延遲["e"] : "100|150|200"
        E技能列表 := StrSplit(E序列, "|")
        E延遲列表 := StrSplit(E延遲, "|")
        
        E技能1 := 技能連段GUI.Add("DropDownList", "x85 y207 w60 h25 R3", 技能選項)
        E技能1.Text := (E技能列表.Length >= 1) ? E技能列表[1] : "OFF"
        技能連段GUI.Add("Text", "x150 y210 w25 h25 c0xFFFFFF BackgroundTrans Center", "→")
        
        E技能2 := 技能連段GUI.Add("DropDownList", "x175 y207 w60 h25 R3", 技能選項)
        E技能2.Text := (E技能列表.Length >= 2) ? E技能列表[2] : "OFF"
        技能連段GUI.Add("Text", "x240 y210 w25 h25 c0xFFFFFF BackgroundTrans Center", "→")
        
        E技能3 := 技能連段GUI.Add("DropDownList", "x265 y207 w60 h25 R3", 技能選項)
        E技能3.Text := (E技能列表.Length >= 3) ? E技能列表[3] : "OFF"
        
        技能連段GUI.Add("Text", "x340 y210 w50 h25 c0xFFD700 BackgroundTrans", "延遲:")
        E延遲1 := 技能連段GUI.Add("Edit", "x390 y207 w40 h25 Number")
        E延遲1.Text := (E延遲列表.Length >= 1) ? E延遲列表[1] : "100"
        E延遲2 := 技能連段GUI.Add("Edit", "x435 y207 w40 h25 Number")
        E延遲2.Text := (E延遲列表.Length >= 2) ? E延遲列表[2] : "150"
        E延遲3 := 技能連段GUI.Add("Edit", "x480 y207 w40 h25 Number")
        E延遲3.Text := (E延遲列表.Length >= 3) ? E延遲列表[3] : "200"
        技能連段GUI.Add("Text", "x525 y210 w30 h25 c0xC0C0C0 BackgroundTrans", "ms")
        
        ; R技能連段設定
        技能連段GUI.Add("Text", "x30 y245 w50 h25 c0xDDA0DD BackgroundTrans", "🌟 R →")
        
        R序列 := 技能連段序列.Has("r") ? 技能連段序列["r"] : "OFF|OFF|OFF"
        R延遲 := 技能連段延遲.Has("r") ? 技能連段延遲["r"] : "100|150|200"
        R技能列表 := StrSplit(R序列, "|")
        R延遲列表 := StrSplit(R延遲, "|")
        
        R技能1 := 技能連段GUI.Add("DropDownList", "x85 y242 w60 h25 R3", 技能選項)
        R技能1.Text := (R技能列表.Length >= 1) ? R技能列表[1] : "OFF"
        技能連段GUI.Add("Text", "x150 y245 w25 h25 c0xFFFFFF BackgroundTrans Center", "→")
        
        R技能2 := 技能連段GUI.Add("DropDownList", "x175 y242 w60 h25 R3", 技能選項)
        R技能2.Text := (R技能列表.Length >= 2) ? R技能列表[2] : "OFF"
        技能連段GUI.Add("Text", "x240 y245 w25 h25 c0xFFFFFF BackgroundTrans Center", "→")
        
        R技能3 := 技能連段GUI.Add("DropDownList", "x265 y242 w60 h25 R3", 技能選項)
        R技能3.Text := (R技能列表.Length >= 3) ? R技能列表[3] : "OFF"
        
        技能連段GUI.Add("Text", "x340 y245 w50 h25 c0xFFD700 BackgroundTrans", "延遲:")
        R延遲1 := 技能連段GUI.Add("Edit", "x390 y242 w40 h25 Number")
        R延遲1.Text := (R延遲列表.Length >= 1) ? R延遲列表[1] : "100"
        R延遲2 := 技能連段GUI.Add("Edit", "x435 y242 w40 h25 Number")
        R延遲2.Text := (R延遲列表.Length >= 2) ? R延遲列表[2] : "150"
        R延遲3 := 技能連段GUI.Add("Edit", "x480 y242 w40 h25 Number")
        R延遲3.Text := (R延遲列表.Length >= 3) ? R延遲列表[3] : "200"
        技能連段GUI.Add("Text", "x525 y245 w30 h25 c0xC0C0C0 BackgroundTrans", "ms")
        
        ; T技能連段設定
        技能連段GUI.Add("Text", "x30 y280 w50 h25 c0xFFA500 BackgroundTrans", "🔱 T →")
        
        T序列 := 技能連段序列.Has("t") ? 技能連段序列["t"] : "OFF|OFF|OFF"
        T延遲 := 技能連段延遲.Has("t") ? 技能連段延遲["t"] : "100|150|200"
        T技能列表 := StrSplit(T序列, "|")
        T延遲列表 := StrSplit(T延遲, "|")
        
        T技能1 := 技能連段GUI.Add("DropDownList", "x85 y277 w60 h25 R3", 技能選項)
        T技能1.Text := (T技能列表.Length >= 1) ? T技能列表[1] : "OFF"
        技能連段GUI.Add("Text", "x150 y280 w25 h25 c0xFFFFFF BackgroundTrans Center", "→")
        
        T技能2 := 技能連段GUI.Add("DropDownList", "x175 y277 w60 h25 R3", 技能選項)
        T技能2.Text := (T技能列表.Length >= 2) ? T技能列表[2] : "OFF"
        技能連段GUI.Add("Text", "x240 y280 w25 h25 c0xFFFFFF BackgroundTrans Center", "→")
        
        T技能3 := 技能連段GUI.Add("DropDownList", "x265 y277 w60 h25 R3", 技能選項)
        T技能3.Text := (T技能列表.Length >= 3) ? T技能列表[3] : "OFF"
        
        技能連段GUI.Add("Text", "x340 y280 w50 h25 c0xFFD700 BackgroundTrans", "延遲:")
        T延遲1 := 技能連段GUI.Add("Edit", "x390 y277 w40 h25 Number")
        T延遲1.Text := (T延遲列表.Length >= 1) ? T延遲列表[1] : "100"
        T延遲2 := 技能連段GUI.Add("Edit", "x435 y277 w40 h25 Number")
        T延遲2.Text := (T延遲列表.Length >= 2) ? T延遲列表[2] : "150"
        T延遲3 := 技能連段GUI.Add("Edit", "x480 y277 w40 h25 Number")
        T延遲3.Text := (T延遲列表.Length >= 3) ? T延遲列表[3] : "200"
        技能連段GUI.Add("Text", "x525 y280 w30 h25 c0xC0C0C0 BackgroundTrans", "ms")
        
        ; === 說明區域 ===
        技能連段GUI.SetFont("s9", "Microsoft YaHei UI")
        技能連段GUI.Add("Text", "x30 y320 w540 h65 c0xC0C0C0 BackgroundTrans", 
            "💡 使用說明：當按下觸發按鍵時，系統會按照設定的序列和延遲時間依序釋放技能。`n" .
            "   OFF = 不執行該步驟 | 延遲單位：毫秒(ms) | 建議延遲：100-500ms`n" .
            "⚠️ 重要提醒：技能連段功能需要先按 F10 啟用高級功能才會生效！")
        
        ; === 按鈕區域 ===
        技能連段GUI.SetFont("s11 Bold", "Microsoft YaHei UI")
        
        ; 儲存按鈕 - 現代風格漸層效果
        儲存按鈕 := 技能連段GUI.Add("Button", "x130 y400 w120 h35", "💾 儲存設定")
        儲存按鈕.SetFont("s11 Bold", "Microsoft YaHei UI")
        儲存按鈕.OnEvent("Click", 儲存技能連段設定_事件)
        
        ; 取消按鈕
        取消按鈕 := 技能連段GUI.Add("Button", "x270 y400 w120 h35", "❌ 取消")
        取消按鈕.SetFont("s11 Bold", "Microsoft YaHei UI")
        取消按鈕.OnEvent("Click", (*) => 技能連段GUI.Destroy())
        
        ; 重製設定按鈕
        重製按鈕 := 技能連段GUI.Add("Button", "x410 y400 w120 h35", "🔄 重製設定")
        重製按鈕.SetFont("s11 Bold", "Microsoft YaHei UI")
        重製按鈕.OnEvent("Click", 重製技能連段設定_事件)
        
        ; 儲存控制項引用供後續使用
        技能連段GUI.狀態下拉 := 狀態下拉
        技能連段GUI.Q技能1 := Q技能1
        技能連段GUI.Q技能2 := Q技能2
        技能連段GUI.Q技能3 := Q技能3
        技能連段GUI.Q延遲1 := Q延遲1
        技能連段GUI.Q延遲2 := Q延遲2
        技能連段GUI.Q延遲3 := Q延遲3
        技能連段GUI.W技能1 := W技能1
        技能連段GUI.W技能2 := W技能2
        技能連段GUI.W技能3 := W技能3
        技能連段GUI.W延遲1 := W延遲1
        技能連段GUI.W延遲2 := W延遲2
        技能連段GUI.W延遲3 := W延遲3
        技能連段GUI.E技能1 := E技能1
        技能連段GUI.E技能2 := E技能2
        技能連段GUI.E技能3 := E技能3
        技能連段GUI.E延遲1 := E延遲1
        技能連段GUI.E延遲2 := E延遲2
        技能連段GUI.E延遲3 := E延遲3
        技能連段GUI.R技能1 := R技能1
        技能連段GUI.R技能2 := R技能2
        技能連段GUI.R技能3 := R技能3
        技能連段GUI.R延遲1 := R延遲1
        技能連段GUI.R延遲2 := R延遲2
        技能連段GUI.R延遲3 := R延遲3
        技能連段GUI.T技能1 := T技能1
        技能連段GUI.T技能2 := T技能2
        技能連段GUI.T技能3 := T技能3
        技能連段GUI.T延遲1 := T延遲1
        技能連段GUI.T延遲2 := T延遲2
        技能連段GUI.T延遲3 := T延遲3
        
        ; 顯示GUI
        技能連段GUI.Show("w580 h460")
        
    } catch Error as err {
        SmartMsgBox("創建技能連段GUI時發生錯誤:`n" . err.message, "錯誤", 0x10)
    }
}

; 儲存技能連段設定事件處理函數
儲存技能連段設定_事件(*) {
    global 技能連段狀態, 技能連段序列, 技能連段延遲, 技能連段GUI
    
    try {
        ; 儲存狀態
        技能連段狀態 := 技能連段GUI.狀態下拉.Text
        
        ; 儲存Q技能設定
        Q新序列 := 技能連段GUI.Q技能1.Text . "|" . 技能連段GUI.Q技能2.Text . "|" . 技能連段GUI.Q技能3.Text
        Q新延遲 := 技能連段GUI.Q延遲1.Text . "|" . 技能連段GUI.Q延遲2.Text . "|" . 技能連段GUI.Q延遲3.Text
        技能連段序列["q"] := Q新序列
        技能連段延遲["q"] := Q新延遲
        
        ; 儲存W技能設定
        W新序列 := 技能連段GUI.W技能1.Text . "|" . 技能連段GUI.W技能2.Text . "|" . 技能連段GUI.W技能3.Text
        W新延遲 := 技能連段GUI.W延遲1.Text . "|" . 技能連段GUI.W延遲2.Text . "|" . 技能連段GUI.W延遲3.Text
        技能連段序列["w"] := W新序列
        技能連段延遲["w"] := W新延遲
        
        ; 儲存E技能設定
        E新序列 := 技能連段GUI.E技能1.Text . "|" . 技能連段GUI.E技能2.Text . "|" . 技能連段GUI.E技能3.Text
        E新延遲 := 技能連段GUI.E延遲1.Text . "|" . 技能連段GUI.E延遲2.Text . "|" . 技能連段GUI.E延遲3.Text
        技能連段序列["e"] := E新序列
        技能連段延遲["e"] := E新延遲
        
        ; 儲存R技能設定
        R新序列 := 技能連段GUI.R技能1.Text . "|" . 技能連段GUI.R技能2.Text . "|" . 技能連段GUI.R技能3.Text
        R新延遲 := 技能連段GUI.R延遲1.Text . "|" . 技能連段GUI.R延遲2.Text . "|" . 技能連段GUI.R延遲3.Text
        技能連段序列["r"] := R新序列
        技能連段延遲["r"] := R新延遲
        
        ; 儲存T技能設定
        T新序列 := 技能連段GUI.T技能1.Text . "|" . 技能連段GUI.T技能2.Text . "|" . 技能連段GUI.T技能3.Text
        T新延遲 := 技能連段GUI.T延遲1.Text . "|" . 技能連段GUI.T延遲2.Text . "|" . 技能連段GUI.T延遲3.Text
        技能連段序列["t"] := T新序列
        技能連段延遲["t"] := T新延遲
        
        ; 儲存到INI檔案
        儲存技能連段設定()
        
        ShowToolTip("✅ 技能連段設定已儲存", 2000, 1)
        技能連段GUI.Destroy()
        
    } catch Error as err {
        SmartMsgBox("儲存設定時發生錯誤:`n" . err.message, "錯誤", 0x10)
    }
}

; 測試技能連段事件處理函數
; 重製技能連段設定事件處理函數
重製技能連段設定_事件(*) {
    global 技能連段GUI
    
    ; 確認對話框 - 使用SmartMsgBox確保顯示在最上層
    result := SmartMsgBox("確定要重製所有技能連段設定為預設值嗎？`n`n這將會：`n• 將所有技能序列重設為 OFF`n• 將所有延遲重設為預設值`n• 此操作無法復原", "重製設定確認", 0x30 + 0x1)
    
    if (result = "OK") {
        ; 重設所有下拉選單為OFF
        技能連段GUI.Q技能1.Text := "OFF"
        技能連段GUI.Q技能2.Text := "OFF" 
        技能連段GUI.Q技能3.Text := "OFF"
        技能連段GUI.W技能1.Text := "OFF"
        技能連段GUI.W技能2.Text := "OFF"
        技能連段GUI.W技能3.Text := "OFF"
        技能連段GUI.E技能1.Text := "OFF"
        技能連段GUI.E技能2.Text := "OFF"
        技能連段GUI.E技能3.Text := "OFF"
        技能連段GUI.R技能1.Text := "OFF"
        技能連段GUI.R技能2.Text := "OFF"
        技能連段GUI.R技能3.Text := "OFF"
        技能連段GUI.T技能1.Text := "OFF"
        技能連段GUI.T技能2.Text := "OFF"
        技能連段GUI.T技能3.Text := "OFF"
        
        ; 重設所有延遲為預設值
        技能連段GUI.Q延遲1.Text := "100"
        技能連段GUI.Q延遲2.Text := "150"
        技能連段GUI.Q延遲3.Text := "200"
        技能連段GUI.W延遲1.Text := "100"
        技能連段GUI.W延遲2.Text := "150"
        技能連段GUI.W延遲3.Text := "200"
        技能連段GUI.E延遲1.Text := "100"
        技能連段GUI.E延遲2.Text := "150"
        技能連段GUI.E延遲3.Text := "200"
        技能連段GUI.R延遲1.Text := "100"
        技能連段GUI.R延遲2.Text := "150"
        技能連段GUI.R延遲3.Text := "200"
        技能連段GUI.T延遲1.Text := "100"
        技能連段GUI.T延遲2.Text := "150"
        技能連段GUI.T延遲3.Text := "200"
        
        ShowToolTip("🔄 技能連段設定已重製為預設值", 2000, 1)
    }
}

; 載入技能連段設定
載入技能連段設定() {
    global 技能連段狀態, 技能連段序列, 技能連段延遲, CONFIG_FILE
    
    try {
        技能連段狀態 := IniRead(CONFIG_FILE, "技能連段", "狀態", "關閉")
        
        ; 載入各技能的連段設定
        技能列表 := ["q", "w", "e", "r", "t"]
        for 技能 in 技能列表 {
            序列 := IniRead(CONFIG_FILE, "技能連段", 技能 . "_序列", "OFF|OFF|OFF")
            延遲 := IniRead(CONFIG_FILE, "技能連段", 技能 . "_延遲", "100|150|200")
            
            技能連段序列[技能] := 序列
            技能連段延遲[技能] := 延遲
        }
        
    } catch Error as err {
        ShowToolTip("⚠️ 載入技能連段設定失敗: " . err.message, 3000, 1)
        ; 使用預設值
        技能連段狀態 := "關閉"
        技能連段序列 := Map()
        技能連段延遲 := Map()
    }
}

; 儲存技能連段設定
儲存技能連段設定() {
    global 技能連段狀態, 技能連段序列, 技能連段延遲, CONFIG_FILE
    
    try {
        IniWrite(技能連段狀態, CONFIG_FILE, "技能連段", "狀態")
        
        ; 儲存各技能的連段設定
        for 技能, 序列 in 技能連段序列 {
            IniWrite(序列, CONFIG_FILE, "技能連段", 技能 . "_序列")
            if (技能連段延遲.Has(技能)) {
                IniWrite(技能連段延遲[技能], CONFIG_FILE, "技能連段", 技能 . "_延遲")
            }
        }
        
    } catch Error as err {
        ShowToolTip("⚠️ 儲存技能連段設定失敗: " . err.message, 3000, 1)
    }
}

; ======================================================================================================
; 自動引爆地雷功能
; ======================================================================================================

; 載入地雷設定
載入地雷設定() {
    global 地雷功能狀態, 地雷按鍵設定, 位移地雷按鍵設定, 位移地雷延遲, CONFIG_FILE
    
    try {
        ; 載入功能狀態
        狀態 := IniRead(CONFIG_FILE, "地雷功能", "狀態", "關閉")
        地雷功能狀態 := (狀態 = "開啟")
        
        ; 載入各技能按鍵的地雷設定
        for 技能 in ["Q", "W", "E", "R", "T"] {
            地雷設定 := IniRead(CONFIG_FILE, "地雷功能", 技能 . "_地雷", "關閉")
            地雷按鍵設定[技能] := (地雷設定 = "開啟")
            
            位移地雷設定 := IniRead(CONFIG_FILE, "地雷功能", 技能 . "_位移地雷", "關閉")
            位移地雷按鍵設定[技能] := (位移地雷設定 = "開啟")
            
            延遲 := IniRead(CONFIG_FILE, "地雷功能", 技能 . "_位移延遲", "300")
            位移地雷延遲[技能] := Integer(延遲)
        }
        
    } catch Error as err {
        ShowToolTip("⚠️ 載入地雷設定失敗: " . err.message, 3000, 1)
        ; 使用預設值
        地雷功能狀態 := false
        for 技能 in ["Q", "W", "E", "R", "T"] {
            地雷按鍵設定[技能] := false
            位移地雷按鍵設定[技能] := false
            位移地雷延遲[技能] := 300
        }
    }
}

; 儲存地雷設定
儲存地雷設定() {
    global 地雷功能狀態, 地雷按鍵設定, 位移地雷按鍵設定, 位移地雷延遲, CONFIG_FILE
    
    try {
        ; 儲存功能狀態
        IniWrite((地雷功能狀態 ? "開啟" : "關閉"), CONFIG_FILE, "地雷功能", "狀態")
        
        ; 儲存各技能按鍵的地雷設定
        for 技能 in ["Q", "W", "E", "R", "T"] {
            IniWrite((地雷按鍵設定[技能] ? "開啟" : "關閉"), CONFIG_FILE, "地雷功能", 技能 . "_地雷")
            IniWrite((位移地雷按鍵設定[技能] ? "開啟" : "關閉"), CONFIG_FILE, "地雷功能", 技能 . "_位移地雷")
            IniWrite(位移地雷延遲[技能], CONFIG_FILE, "地雷功能", 技能 . "_位移延遲")
        }
        
        ShowToolTip("✅ 地雷設定已儲存", 2000, 1)
        
    } catch Error as err {
        SmartMsgBox("儲存地雷設定時發生錯誤:`n" . err.message, "錯誤", 0x10)
    }
}

; 處理地雷觸發
處理地雷觸發(按鍵) {
    global 地雷功能狀態, 地雷按鍵設定, 位移地雷按鍵設定, 位移地雷延遲, 當前長按地雷按鍵
    
    ; 檢查地雷功能是否開啟
    if (!地雷功能狀態) {
        return
    }
    
    ; 處理普通地雷 - 長按D
    if (地雷按鍵設定.Has(按鍵) && 地雷按鍵設定[按鍵]) {
        if (當前長按地雷按鍵 != "") {
            ; 如果已有其他按鍵在長按，先釋放
            Send("{d up}")
            當前長按地雷按鍵 := ""
        }
        ; 開始長按D
        Send("{d down}")
        當前長按地雷按鍵 := 按鍵
        ShowToolTip("💣 地雷引爆中... (按鍵: " . 按鍵 . ")", 1000, 2)
    }
    
    ; 處理位移地雷 - 延遲後單次觸發
    if (位移地雷按鍵設定.Has(按鍵) && 位移地雷按鍵設定[按鍵]) {
        延遲時間 := 位移地雷延遲[按鍵]
        ShowToolTip("🌪️ 位移地雷準備中... (" . 延遲時間 . "ms)", 延遲時間, 3)
        
        ; 使用定時器延遲觸發
        延遲時間Copy := 延遲時間
        按鍵Copy := 按鍵
        ; 創建唯一的定時器名稱
        timerName := "位移地雷_" . 按鍵Copy . "_" . A_TickCount
        
        ; 設定定時器觸發位移地雷
        SetTimer(() => 定時器觸發位移地雷(按鍵Copy), -延遲時間Copy)
    }
}

; 定時器觸發位移地雷函數
定時器觸發位移地雷(按鍵) {
    Send("{d}")
    ShowToolTip("💥 位移地雷引爆! (按鍵: " . 按鍵 . ")", 1000, 3)
}

; 釋放地雷長按
釋放地雷長按(按鍵) {
    global 地雷功能狀態, 地雷按鍵設定, 當前長按地雷按鍵
    
    ; 檢查是否需要釋放長按
    if (!地雷功能狀態 || 當前長按地雷按鍵 != 按鍵) {
        return
    }
    
    ; 檢查是否為地雷按鍵
    if (地雷按鍵設定.Has(按鍵) && 地雷按鍵設定[按鍵]) {
        Send("{d up}")
        當前長按地雷按鍵 := ""
        ShowToolTip("🔹 地雷引爆結束 (按鍵: " . 按鍵 . ")", 1000, 2)
    }
}

; 顯示地雷設置GUI
Show_地雷設置GUI() {
    global 地雷功能狀態, 地雷按鍵設定, 位移地雷按鍵設定, 位移地雷延遲, 地雷GUI
    
    try {
        ; 確保延遲設定已載入
        載入地雷設定()
        
        ; 創建現代化地雷設置GUI
        地雷GUI := Gui("-MinimizeBox -MaximizeBox", "💣 自動引爆地雷設置中心")
        地雷GUI.BackColor := "0x1E1E1E"  ; 深色背景
        地雷GUI.SetFont("s11", "Segoe UI")
        地雷GUI.MarginX := 20
        地雷GUI.MarginY := 20
        
        ; 📋 標題區域
        titleText := 地雷GUI.Add("Text", "x20 y20 w560 h40 +Center", "💣 自動引爆地雷設置中心")
        titleText.SetFont("s16 Bold", "Segoe UI")
        titleText.Opt("+c0xFFFFFF")
        
        ; 功能說明
        descText := 地雷GUI.Add("Text", "x20 y65 w560 h60 +Center", 
            "⚡ 普通地雷: 按下技能鍵時自動長按D鍵引爆`n" . 
            "🌪️ 位移地雷: 按下技能鍵後延遲指定時間自動引爆`n" . 
            "⚠️ 需要打開F10功能才會啟用")
        descText.SetFont("s9", "Segoe UI")
        descText.Opt("+c0xCCCCCC")
        
        ; 功能開關
        statusText := 地雷GUI.Add("Text", "x20 y140 w100 h25", "功能狀態:")
        statusText.SetFont("s11 Bold", "Segoe UI")
        statusText.Opt("+c0xFFFFFF")
        
        statusToggle := 地雷GUI.Add("CheckBox", "x130 y140 w80 h25 +c0xFFFFFF", "開啟")
        statusToggle.Value := 地雷功能狀態
        statusToggle.SetFont("s10", "Segoe UI")
        
        ; 技能按鍵設定標題
        skillTitle := 地雷GUI.Add("Text", "x20 y200 w560 h30 +Center", "🎯 技能按鍵設定")
        skillTitle.SetFont("s14 Bold", "Segoe UI")
        skillTitle.Opt("+c0xFFFFFF")
        
        ; 表格標題
        headerSkill := 地雷GUI.Add("Text", "x60 y240 w60 h25 +Center", "技能")
        headerSkill.Opt("+c0xFFFFFF")
        
        headerNormal := 地雷GUI.Add("Text", "x140 y240 w100 h25 +Center", "💣 普通地雷")
        headerNormal.Opt("+c0xFFFFFF")
        
        headerDisplace := 地雷GUI.Add("Text", "x260 y240 w100 h25 +Center", "🌪️ 位移地雷")
        headerDisplace.Opt("+c0xFFFFFF")
        
        headerDelay := 地雷GUI.Add("Text", "x380 y240 w80 h25 +Center", "延遲(ms)")
        headerDelay.Opt("+c0xFFFFFF")
        
        headerAdjust := 地雷GUI.Add("Text", "x480 y240 w80 h25 +Center", "調整延遲")
        headerAdjust.Opt("+c0xFFFFFF")
        
        ; 儲存控制項引用
        地雷控制項 := Map()
        位移地雷控制項 := Map()
        延遲控制項 := Map()
        
        ; 生成技能設定行
        yPos := 270
        
        for i, 技能 in ["Q", "W", "E", "R", "T"] {
            ; 技能名稱 - 使用簡單的白色文字，不設背景色
            skillBox := 地雷GUI.Add("Text", "x60 y" . yPos . " w60 h30 +Center +Border", 技能)
            skillBox.SetFont("s12 Bold", "Segoe UI")
            skillBox.Opt("+c0xFFFFFF")  ; 白色文字
            
            ; 普通地雷設定
            地雷控制項[技能] := 地雷GUI.Add("CheckBox", "x155 y" . (yPos + 5) . " w70 h20 +c0xFFFFFF", "啟用")
            地雷控制項[技能].Value := 地雷按鍵設定[技能]
            地雷控制項[技能].SetFont("s9", "Segoe UI")
            
            ; 位移地雷設定
            位移地雷控制項[技能] := 地雷GUI.Add("CheckBox", "x275 y" . (yPos + 5) . " w70 h20 +c0xFFFFFF", "啟用")
            位移地雷控制項[技能].Value := 位移地雷按鍵設定[技能]
            位移地雷控制項[技能].SetFont("s9", "Segoe UI")
            
            ; 延遲顯示
            currentDelay := 位移地雷延遲[技能]  ; 確保獲取當前延遲值
            延遲控制項[技能] := 地雷GUI.Add("Text", "x390 y" . (yPos + 5) . " w60 h20 +Center", String(currentDelay))
            延遲控制項[技能].SetFont("s9", "Segoe UI")
            延遲控制項[技能].Opt("+c0xFFFFFF")  ; 白色文字
            
            ; 調整延遲按鈕 - 創建專用的調整函數避免閉包問題
            adjustBtn := 地雷GUI.Add("Button", "x490 y" . yPos . " w70 h30", "⚙️ 調整")
            adjustBtn.SetFont("s8", "Segoe UI")
            
            ; 為每個技能創建獨立的調整函數
            switch 技能 {
                case "Q":
                    adjustBtn.OnEvent("Click", (*) => 調整位移地雷延遲("Q", 延遲控制項["Q"]))
                case "W":
                    adjustBtn.OnEvent("Click", (*) => 調整位移地雷延遲("W", 延遲控制項["W"]))
                case "E":
                    adjustBtn.OnEvent("Click", (*) => 調整位移地雷延遲("E", 延遲控制項["E"]))
                case "R":
                    adjustBtn.OnEvent("Click", (*) => 調整位移地雷延遲("R", 延遲控制項["R"]))
                case "T":
                    adjustBtn.OnEvent("Click", (*) => 調整位移地雷延遲("T", 延遲控制項["T"]))
            }
            
            yPos += 40
        }
        
        ; 按鈕區域
        btnY := yPos + 30
        
        ; 儲存按鈕
        saveBtn := 地雷GUI.Add("Button", "x130 y" . btnY . " w120 h40", "💾 儲存設定")
        saveBtn.SetFont("s11 Bold", "Segoe UI")
        saveBtn.OnEvent("Click", (*) => 儲存地雷設定_事件(statusToggle, 地雷控制項, 位移地雷控制項))
        
        ; 重製設定按鈕
        resetBtn := 地雷GUI.Add("Button", "x270 y" . btnY . " w120 h40", "🔄 重製設定")
        resetBtn.SetFont("s11 Bold", "Segoe UI")
        resetBtn.OnEvent("Click", (*) => 重製地雷設定_事件())
        
        ; 關閉按鈕
        closeBtn := 地雷GUI.Add("Button", "x410 y" . btnY . " w120 h40", "❌ 關閉")
        closeBtn.SetFont("s11 Bold", "Segoe UI")
        closeBtn.OnEvent("Click", (*) => 地雷GUI.Destroy())
        
        ; 關閉事件
        地雷GUI.OnEvent("Close", (*) => 地雷GUI.Destroy())
        地雷GUI.OnEvent("Escape", (*) => 地雷GUI.Destroy())
        
        ; 顯示GUI
        地雷GUI.Show("w600 h" . (btnY + 90))
        
    } catch Error as err {
        SmartMsgBox("創建地雷設置GUI時發生錯誤:`n" . err.message, "錯誤", 0x10)
    }
}

; 調整位移地雷延遲
調整位移地雷延遲(技能, 延遲顯示控制項) {
    global 位移地雷延遲
    
    ; 創建延遲調整GUI
    delayGUI := Gui("+AlwaysOnTop -MinimizeBox -MaximizeBox", "⏱️ " . 技能 . " 位移地雷延遲調整")
    delayGUI.BackColor := "0x1E1E1E"  ; 深色背景
    delayGUI.SetFont("s11", "Segoe UI")
    delayGUI.MarginX := 20
    delayGUI.MarginY := 20
    
    ; 標題
    titleText := delayGUI.Add("Text", "x20 y20 w300 h30 +Center", "🌪️ " . 技能 . " 位移地雷延遲設定")
    titleText.SetFont("s12 Bold", "Segoe UI")
    titleText.Opt("+c0xFFFFFF")  ; 白色文字
    
    ; 說明
    descText := delayGUI.Add("Text", "x20 y55 w300 h40 +Center", "設定按下 " . 技能 . " 鍵後多久自動引爆地雷`n範圍: 50-2000毫秒")
    descText.SetFont("s9", "Segoe UI")
    descText.Opt("+c0xCCCCCC")  ; 淺灰色文字
    
    ; 當前值顯示
    currentText := delayGUI.Add("Text", "x20 y105 w80 h25", "當前延遲:")
    currentText.SetFont("s10", "Segoe UI")
    currentText.Opt("+c0xFFFFFF")  ; 白色文字
    
    delayEdit := delayGUI.Add("Edit", "x105 y100 w80 h30 +Center", 位移地雷延遲[技能])
    delayEdit.SetFont("s11", "Segoe UI")
    
    msText := delayGUI.Add("Text", "x195 y105 w30 h25", "ms")
    msText.SetFont("s10", "Segoe UI")
    msText.Opt("+c0xFFFFFF")  ; 白色文字
    
    ; 預設值按鈕
    presetText := delayGUI.Add("Text", "x20 y145 w300 h20 +Center", "快速設定:")
    presetText.SetFont("s9", "Segoe UI")
    presetText.Opt("+c0xCCCCCC")  ; 淺灰色文字
    
    ; 預設值按鈕組
    preset100 := delayGUI.Add("Button", "x30 y170 w50 h25", "100")
    preset100.OnEvent("Click", (*) => delayEdit.Text := "100")
    
    preset200 := delayGUI.Add("Button", "x90 y170 w50 h25", "200")
    preset200.OnEvent("Click", (*) => delayEdit.Text := "200")
    
    preset300 := delayGUI.Add("Button", "x150 y170 w50 h25", "300")
    preset300.OnEvent("Click", (*) => delayEdit.Text := "300")
    
    preset500 := delayGUI.Add("Button", "x210 y170 w50 h25", "500")
    preset500.OnEvent("Click", (*) => delayEdit.Text := "500")
    
    preset1000 := delayGUI.Add("Button", "x270 y170 w50 h25", "1000")
    preset1000.OnEvent("Click", (*) => delayEdit.Text := "1000")
    
    ; 確認按鈕
    confirmBtn := delayGUI.Add("Button", "x80 y210 w80 h35", "✅ 確認")
    confirmBtn.SetFont("s10 Bold", "Segoe UI")
    
    ; 取消按鈕
    cancelBtn := delayGUI.Add("Button", "x180 y210 w80 h35", "❌ 取消")
    cancelBtn.SetFont("s10 Bold", "Segoe UI")
    
    ; 綁定事件
    confirmBtn.OnEvent("Click", (*) => 確認位移地雷延遲(技能, delayEdit, 延遲顯示控制項, delayGUI))
    cancelBtn.OnEvent("Click", (*) => delayGUI.Destroy())
    
    ; 關閉事件
    delayGUI.OnEvent("Close", (*) => delayGUI.Destroy())
    delayGUI.OnEvent("Escape", (*) => delayGUI.Destroy())
    
    ; 顯示GUI
    delayGUI.Show("w340 h270")
    delayEdit.Focus()
}

; 確認位移地雷延遲設定
確認位移地雷延遲(技能, delayEdit, 延遲顯示控制項, delayGUI) {
    global 位移地雷延遲
    
    newDelay := delayEdit.Text
    if (newDelay == "" || !IsNumber(newDelay)) {
        SmartMsgBox("⚠️ 請輸入有效的數字", "輸入錯誤", 0x30)
        delayEdit.Focus()
        return
    }
    
    newDelay := Integer(newDelay)
    if (newDelay < 50 || newDelay > 2000) {
        SmartMsgBox("⚠️ 延遲時間必須在 50-2000ms 範圍內", "輸入錯誤", 0x30)
        delayEdit.Focus()
        return
    }
    
    ; 更新延遲設定
    位移地雷延遲[技能] := newDelay
    ; 更新GUI顯示
    延遲顯示控制項.Text := String(newDelay)
    ; 強制重繪控制項
    延遲顯示控制項.Redraw()
    ; 立即儲存到INI檔案
    儲存地雷設定()
    
    ShowToolTip("✅ " . 技能 . " 位移地雷延遲已設為: " . newDelay . "ms", 2000, 1)
    delayGUI.Destroy()
}

; 儲存地雷設定事件
; 儲存地雷設定事件
儲存地雷設定_事件(statusToggle, 地雷控制項, 位移地雷控制項) {
    global 地雷功能狀態, 地雷按鍵設定, 位移地雷按鍵設定, 地雷GUI
    
    try {
        ; 更新功能狀態
        地雷功能狀態 := statusToggle.Value
        
        ; 更新各技能設定並檢查互斥
        for 技能 in ["Q", "W", "E", "R", "T"] {
            normalValue := 地雷控制項[技能].Value
            displaceValue := 位移地雷控制項[技能].Value
            
            ; 互斥邏輯：不能同時啟用普通地雷和位移地雷
            if (normalValue && displaceValue) {
                ; 暫時隱藏地雷GUI避免被覆蓋
                地雷GUI.Hide()
                result := MsgBox("⚠️ 技能 " . 技能 . " 不能同時啟用普通地雷和位移地雷`n請選擇其中一種模式", "設定衝突", 0x30)
                地雷GUI.Show()
                return
            }
            
            地雷按鍵設定[技能] := normalValue
            位移地雷按鍵設定[技能] := displaceValue
        }
        
        ; 儲存設定到INI
        儲存地雷設定()
        
        ShowToolTip("✅ 地雷設定已儲存", 2000, 1)
        地雷GUI.Destroy()
        
    } catch Error as err {
        SmartMsgBox("儲存設定時發生錯誤:`n" . err.message, "錯誤", 0x10)
    }
}

; 重製地雷設定事件
重製地雷設定_事件() {
    global 地雷功能狀態, 地雷按鍵設定, 位移地雷按鍵設定, 位移地雷延遲, 地雷GUI
    
    ; 確認對話框
    result := SmartMsgBox("確定要重製所有地雷設定為預設值嗎？`n`n這將會：`n• 關閉地雷功能`n• 關閉所有技能的地雷設定`n• 重設所有延遲為300ms`n• 此操作無法復原", "重製設定確認", 0x30 + 0x1)
    
    if (result = "OK") {
        ; 重製為預設值
        地雷功能狀態 := false
        for 技能 in ["Q", "W", "E", "R", "T"] {
            地雷按鍵設定[技能] := false
            位移地雷按鍵設定[技能] := false
            位移地雷延遲[技能] := 300
        }
        
        ; 儲存設定
        儲存地雷設定()
        
        ; 關閉GUI重新開啟
        地雷GUI.Destroy()
        Show_地雷設置GUI()
        
        ShowToolTip("🔄 地雷設定已重製為預設值", 2500, 1)
    }
}

; ======================================================================================================
; 滑鼠連點功能
; ======================================================================================================

; 顯示滑鼠連點設置GUI - 修正對齊版本
Show_MouseClickGui() {
    global 連點模式, 滑鼠連點速度
    
    ; 創建現代化滑鼠連點設置GUI
    連點設置GUI := Gui("+AlwaysOnTop -MinimizeBox -MaximizeBox +Resize", "🖱️ 滑鼠連點設置中心")
    連點設置GUI.BackColor := "0x1E1E1E"  ; 深色背景
    連點設置GUI.SetFont("s11 Bold", "Segoe UI")
    連點設置GUI.MarginX := 20
    連點設置GUI.MarginY := 20
    
    ; 📋 標題區域
    title := 連點設置GUI.Add("Text", "x20 y20 w360 h45 Center c0xFFFFFF", "🖱️ 滑鼠連點設置控制台")
    title.SetFont("s16 Bold", "Microsoft YaHei UI")
    
    ; 🎯 當前狀態顯示區
    statusGroup := 連點設置GUI.Add("GroupBox", "x20 y75 w360 h70 c0xC0C0C0", " 📊 當前設置狀態 ")
    statusGroup.SetFont("s10 Bold", "Microsoft YaHei UI")
    
    ; 當前連點模式
    currentMode := 連點設置GUI.Add("Text", "x35 y100 w160 h25 c0x00FF00", "連點模式: " . 連點模式)
    currentMode.SetFont("s10 Bold", "Consolas")
    
    ; 當前連點速度
    currentSpeed := 連點設置GUI.Add("Text", "x205 y100 w160 h25 c0x00FFFF", "連點速度: " . 滑鼠連點速度 . "ms")
    currentSpeed.SetFont("s10 Bold", "Consolas")
    
    ; 🎮 連點模式選擇區
    modeGroup := 連點設置GUI.Add("GroupBox", "x20 y155 w360 h80 c0xC0C0C0", " 🎮 連點模式選擇 ")
    modeGroup.SetFont("s10 Bold", "Microsoft YaHei UI")
    
    ; 滑鼠滾輪按壓按鈕
    wheelBtn := 連點設置GUI.Add("Button", "x40 y185 w150 h35", "🖱️ 滑鼠滾輪按壓")
    wheelBtn.SetFont("s10 Bold", "Microsoft YaHei UI")
    
    ; 滑鼠滾輪按鈕事件處理
    HandleWheelClick() {
        設置連點模式("滑鼠滾輪按壓")
        連點設置GUI.Destroy()
    }
    wheelBtn.OnEvent("Click", (*) => HandleWheelClick())
    
    ; Ctrl + 左鍵按鈕
    ctrlBtn := 連點設置GUI.Add("Button", "x210 y185 w150 h35", "⌨️ Ctrl + 左鍵")
    ctrlBtn.SetFont("s10 Bold", "Microsoft YaHei UI")
    
    ; Ctrl按鈕事件處理
    HandleCtrlClick() {
        設置連點模式("[Ctrl + 左鍵]")
        連點設置GUI.Destroy()
    }
    ctrlBtn.OnEvent("Click", (*) => HandleCtrlClick())
    
    ; 🚀 速度調整區
    speedGroup := 連點設置GUI.Add("GroupBox", "x20 y245 w360 h80 c0xC0C0C0", " ⚡ 連點速度調整 ")
    speedGroup.SetFont("s10 Bold", "Microsoft YaHei UI")
    
    ; 速度調整按鈕
    speedBtn := 連點設置GUI.Add("Button", "x40 y275 w150 h35", "⚙️ 調整連點速度")
    speedBtn.SetFont("s10 Bold", "Microsoft YaHei UI")
    speedBtn.OnEvent("Click", (*) => 調整連點速度())
    
    ; 預設速度說明
    speedInfo := 連點設置GUI.Add("Text", "x210 y275 w150 h35 c0xFFFF00 Center", "範圍: 5~50ms`n越小越快")
    speedInfo.SetFont("s9", "Microsoft YaHei UI")
    
    ; 💡 使用說明區
    infoGroup := 連點設置GUI.Add("GroupBox", "x20 y335 w360 h90 c0xC0C0C0", " 💡 使用說明 ")
    infoGroup.SetFont("s10 Bold", "Microsoft YaHei UI")
    
    ; 說明文字
    infoText := 連點設置GUI.Add("Text", "x35 y360 w330 h50 c0xFFFFFF", 
        "• 滑鼠滾輪按壓: 按住滑鼠中鍵進行連點`n" .
        "• Ctrl + 左鍵: 按住Ctrl + 左鍵進行連點`n" .
        "• 連點速度: 0ms最快，50ms最慢`n" .
        "• 僅在遊戲視窗中生效")
    infoText.SetFont("s9", "Microsoft YaHei UI")
    
    ; 🔧 底部按鈕區
    resetBtn := 連點設置GUI.Add("Button", "x40 y440 w100 h35", "🔄 重置設定")
    resetBtn.SetFont("s10 Bold", "Microsoft YaHei UI")
    resetBtn.OnEvent("Click", (*) => 重置連點設定(連點設置GUI))
    
    ; 關閉按鈕
    closeBtn := 連點設置GUI.Add("Button", "x160 y440 w100 h35", "❌ 關閉視窗")
    closeBtn.SetFont("s10 Bold", "Microsoft YaHei UI")
    closeBtn.OnEvent("Click", (*) => 連點設置GUI.Destroy())
    
    ; 📄 版權資訊
    copyright := 連點設置GUI.Add("Text", "x280 y440 w100 h35 c0x808080 Center", "製作: Sid")
    copyright.SetFont("s8", "Microsoft YaHei UI")
    
    ; 🎬 關閉事件處理
    連點設置GUI.OnEvent("Close", (*) => 連點設置GUI.Destroy())
    連點設置GUI.OnEvent("Escape", (*) => 連點設置GUI.Destroy())
    
    ; 🌟 顯示GUI並居中
    連點設置GUI.Show("w400 h490")
    
    ; 動態更新狀態顯示
    UpdateStatus() {
        currentMode.Text := "連點模式: " . 連點模式
        currentSpeed.Text := "連點速度: " . 滑鼠連點速度 . "ms"
    }
    
    ; 將更新函數存儲到GUI對象中
    連點設置GUI.UpdateStatus := UpdateStatus
}

; 設置連點模式 - 增強版本
設置連點模式(模式) {
    global 連點模式
    連點模式 := 模式
    IniWrite(連點模式, CONFIG_FILE, "按鍵模式切換", "連點模式")
    
    ; 根據模式顯示不同的訊息
    if (模式 = "滑鼠滾輪按壓") {
        ShowToolTip("🖱️ 連點模式: 滑鼠滾輪按壓`n按住滑鼠中鍵進行連點", 2500, 1)
    } else if (模式 = "[Ctrl + 左鍵]") {
        ShowToolTip("⌨️ 連點模式: Ctrl + 左鍵`n按住Ctrl + 左鍵進行連點", 2500, 1)
    } else {
        ShowToolTip("滑鼠連點設為: " . 連點模式, 2000, 1)
    }
}

; 調整連點速度 - 舒適間距版本
調整連點速度() {
    global 滑鼠連點速度
    
    ; 創建現代化速度調整GUI
    speedGUI := Gui("+AlwaysOnTop -MinimizeBox -MaximizeBox", "⚡ 連點速度調整")
    speedGUI.BackColor := "0x2D2D30"
    speedGUI.SetFont("s11", "Microsoft YaHei UI")
    speedGUI.MarginX := 25
    speedGUI.MarginY := 25
    
    ; 標題區 - 增加高度
    title := speedGUI.Add("Text", "x25 y25 w340 h35 Center c0xFFFFFF", "⚡ 連點速度微調控制台")
    title.SetFont("s13 Bold", "Microsoft YaHei UI")
    
    ; 當前速度顯示區 - 增加間距
    currentLabel := speedGUI.Add("Text", "x25 y80 w120 h30 c0x00FFFF", "當前速度:")
    currentLabel.SetFont("s11", "Microsoft YaHei UI")
    currentValue := speedGUI.Add("Text", "x150 y80 w100 h30 c0x00FF00", 滑鼠連點速度 . " ms")
    currentValue.SetFont("s12 Bold", "Consolas")
    
    ; 速度輸入區 - 增加間距
    speedGUI.Add("Text", "x25 y125 w340 h25 c0xFFFFFF", "請輸入新的連點速度 (5-50ms):")
    speedEdit := speedGUI.Add("Edit", "x25 y155 w120 h30 Number", 滑鼠連點速度)
    speedEdit.SetFont("s11", "Consolas")
    speedGUI.Add("Text", "x155 y155 w80 h30 c0x808080", "毫秒 (ms)")
    
    ; 預設值按鈕區標題 - 增加間距
    speedGUI.Add("Text", "x25 y200 w340 h25 c0xFFFFFF", "常用預設值:")
    
    ; 預設值按鈕行 - 加大按鈕和間距
    fastBtn := speedGUI.Add("Button", "x25 y230 w75 h35", "極快(5)")
    fastBtn.OnEvent("Click", (*) => speedEdit.Text := "5")
    
    normalBtn := speedGUI.Add("Button", "x115 y230 w75 h35", "正常(15)")
    normalBtn.OnEvent("Click", (*) => speedEdit.Text := "15")
    
    defaultBtn := speedGUI.Add("Button", "x205 y230 w75 h35", "預設(25)")
    defaultBtn.OnEvent("Click", (*) => speedEdit.Text := "25")
    
    slowBtn := speedGUI.Add("Button", "x295 y230 w75 h35", "較慢(40)")
    slowBtn.OnEvent("Click", (*) => speedEdit.Text := "40")
    
    ; 說明文字區 - 增加間距和高度
    speedGUI.Add("Text", "x25 y285 w340 h35 c0xFFFF00", "💡 提示: 數值越小連點越快，建議值 10-30ms")
    
    ; 按鈕區 - 增加間距和按鈕大小
    confirmBtn := speedGUI.Add("Button", "x80 y340 w100 h40", "✅ 確認")
    cancelBtn := speedGUI.Add("Button", "x210 y340 w100 h40", "❌ 取消")
    
    ; 確認按鈕事件處理函數
    HandleConfirm() {
        新速度 := speedEdit.Text
        if (新速度 = "" || !IsNumber(新速度)) {
            ; 使用SmartMsgBox確保對話框可見
            SmartMsgBox("⚠️ 請輸入有效的數字", "輸入錯誤", 0x30)
            speedEdit.Focus()
            return
        }
        
        新速度 := Integer(新速度)
        if (新速度 < 5 || 新速度 > 50) {
            ; 使用SmartMsgBox確保對話框可見
            SmartMsgBox("⚠️ 連點速度必須在 5-50ms 範圍內", "輸入錯誤", 0x30)
            speedEdit.Focus()
            return
        }
        
        滑鼠連點速度 := 新速度
        IniWrite(滑鼠連點速度, CONFIG_FILE, "按鍵模式切換", "滑鼠連點速度")
        ShowToolTip("✅ 連點速度已設為: " . 滑鼠連點速度 . "ms", 2000, 1)
        speedGUI.Destroy()
    }
    
    ; 綁定事件
    confirmBtn.OnEvent("Click", (*) => HandleConfirm())
    cancelBtn.OnEvent("Click", (*) => speedGUI.Destroy())
    
    ; 關閉事件
    speedGUI.OnEvent("Close", (*) => speedGUI.Destroy())
    speedGUI.OnEvent("Escape", (*) => speedGUI.Destroy())
    
    ; 顯示GUI - 增加尺寸
    speedGUI.Show("w390 h400")
    speedEdit.Focus()
}

; 重置連點設定 - 修正GUI層級問題
重置連點設定(parentGUI := "") {
    global 連點模式, 滑鼠連點速度
    
    ; 先關閉父GUI
    if (IsObject(parentGUI)) {
        parentGUI.Destroy()
    }
    
    ; 確認對話框
    result := SmartMsgBox("確定要重置所有連點設定為預設值嗎？`n`n• 連點模式: 滑鼠滾輪按壓`n• 連點速度: 25ms", 
                     "🔄 重置確認", 0x40 + 0x4)
    
    if (result = "Yes") {
        ; 重置為預設值
        連點模式 := "滑鼠滾輪按壓"
        滑鼠連點速度 := 25
        
        ; 保存設定
        IniWrite(連點模式, CONFIG_FILE, "按鍵模式切換", "連點模式")
        IniWrite(滑鼠連點速度, CONFIG_FILE, "按鍵模式切換", "滑鼠連點速度")
        
        ; 顯示成功訊息
        ShowToolTip("🔄 連點設定已重置為預設值", 2500, 1)
    } else {
        ; 如果取消，重新開啟GUI
        Show_MouseClickGui()
    }
}

; ======================================================================================================
; 滑鼠連點熱鍵（帶視窗檢測）
; ======================================================================================================

; Ctrl + 左鍵連點
~*^LButton:: {
    ; 只有在遊戲視窗中才啟用連點功能
    if (!檢查遊戲視窗()) {
        return
    }
    
    global 連點模式, 滑鼠連點速度, clickStop
    
    if (連點模式 = "[Ctrl + 左鍵]") {
        Sleep(100)
        
        ; 檢查Ctrl鍵狀態，添加安全控制
        if (GetKeyState("Ctrl", "P")) {
            clickStop := false
            
            try {
                ; 開始連點循環，添加更嚴格的條件檢查
                while (GetKeyState("Ctrl", "P") && GetKeyState("LButton", "P") && !clickStop) {
                    ; 安全的Ctrl+Click操作
                    Send("{Ctrl down}")
                    Click()
                    Send("{Ctrl up}")
                    Sleep(滑鼠連點速度)
                    
                    ; 每5次檢查一次是否需要中斷
                    if (Mod(A_Index, 5) = 0 && !WinActive("Path of Exile") && !WinActive("Path of Exile 2")) {
                        break
                    }
                }
            } catch Error as e {
                ; 異常處理：確保釋放Ctrl鍵
                Send("{Ctrl up}")
                clickStop := true
                ShowToolTip("⚠️ 連點異常，已安全停止", 2000, 1)
            } finally {
                ; 最終保證：無論如何都釋放Ctrl鍵
                Send("{Ctrl up}")
                clickStop := true
            }
        }
    }
}

; Ctrl + 左鍵釋放
~*^LButton Up:: {
    ; 只有在遊戲視窗中才處理
    if (!檢查遊戲視窗()) {
        return
    }
    
    global 連點模式, clickStop
    
    if (連點模式 = "[Ctrl + 左鍵]") {
        clickStop := true
    }
}

; 滑鼠滾輪按壓連點
~*MButton:: {
    ; 只有在遊戲視窗中才啟用連點功能
    if (!檢查遊戲視窗()) {
        return
    }
    
    global 連點模式, 滑鼠連點速度, clickStop
    
    if (連點模式 = "滑鼠滾輪按壓") {
        clickStop := false
        
        ; 開始連點循環
        while (GetKeyState("MButton", "P") && !clickStop) {
            Click()
            Sleep(滑鼠連點速度)
        }
    }
}

; 滑鼠滾輪釋放
~*MButton Up:: {
    ; 只有在遊戲視窗中才處理
    if (!檢查遊戲視窗()) {
        return
    }
    
    global 連點模式, clickStop
    
    if (連點模式 = "滑鼠滾輪按壓") {
        clickStop := true
    }
}

F8_智能拾取設置(*) {
    顯示智能拾取設置GUI()
}


; ========================== 十字座標指示器功能 ==========================

; 創建十字指示器
CreateCrosshair(x, y, color := "0xFF0000", size := 20, thickness := 3, transparency := 200, autoClose := true) {
    global CrosshairGUI, CrosshairActive
    
    ; 安全的參數類型轉換
    x := (IsObject(x) && x.Length > 0) ? x[1] : x
    y := (IsObject(y) && y.Length > 0) ? y[1] : y
    size := (IsObject(size) && size.Length > 0) ? size[1] : size
    thickness := (IsObject(thickness) && thickness.Length > 0) ? thickness[1] : thickness
    transparency := (IsObject(transparency) && transparency.Length > 0) ? transparency[1] : transparency
    
    ; 確保都是數字
    x := IsNumber(x) ? Integer(x) : 0
    y := IsNumber(y) ? Integer(y) : 0
    size := IsNumber(size) ? Integer(size) : 20
    thickness := IsNumber(thickness) ? Integer(thickness) : 3
    transparency := IsNumber(transparency) ? Integer(transparency) : 200
    
    ; 如果已有十字指示器，先銷毀
    if (CrosshairActive) {
        DestroyCrosshair()
    }
    
    ; 🎯 確保十字線顏色不會與透明背景衝突
    if (color = "0xFFFFFF" || color = "0xffffff" || color = "FFFFFF" || color = "ffffff") {
        color := "0xFEFEFE"  ; 改為接近白色但不透明的顏色
    }
    
    ; 創建無邊框、置頂的透明GUI
    CrosshairGUI := Gui("+AlwaysOnTop -Caption +ToolWindow +LastFound", "CrosshairIndicator")
    CrosshairGUI.BackColor := "0xFFFFFF"  ; 白色背景用於透明遮罩
    CrosshairGUI.MarginX := 0
    CrosshairGUI.MarginY := 0
    
    ; 設定GUI完全透明背景 - 使用TransColor讓背景完全透明
    WinSetTransColor("0xFFFFFF", CrosshairGUI.Hwnd)  ; 白色變透明
    
    ; 計算十字的位置和大小
    halfSize := size // 2
    
    ; 創建水平線
    HorizontalLine := CrosshairGUI.Add("Text", 
        "x" . (halfSize - (size // 2)) . " y" . (halfSize - thickness//2) . 
        " w" . size . " h" . thickness . " Background" . color)
    
    ; 創建垂直線
    VerticalLine := CrosshairGUI.Add("Text", 
        "x" . (halfSize - thickness//2) . " y" . (halfSize - (size // 2)) . 
        " w" . thickness . " h" . size . " Background" . color)
    
    ; 在指定位置顯示十字
    CrosshairGUI.Show("x" . (x - halfSize) . " y" . (y - halfSize) . " w" . size . " h" . size . " NoActivate")
    
    CrosshairActive := true
    
    ; 可選擇是否自動關閉
    if (autoClose) {
        SetTimer(() => DestroyCrosshair(), -3000)
    }
    
    return CrosshairGUI
}

; 銷毀十字指示器
DestroyCrosshair() {
    global CrosshairGUI, CrosshairActive
    
    if (CrosshairActive && CrosshairGUI) {
        try {
            CrosshairGUI.Destroy()
        } catch {
            ; 忽略錯誤
        }
        CrosshairGUI := ""
        CrosshairActive := false
    }
}

; 顯示座標資訊氣泡
ShowCoordinateBubble(x, y, info := "") {
    ; 安全的參數類型轉換
    x := (IsObject(x) && x.Length > 0) ? x[1] : x
    y := (IsObject(y) && y.Length > 0) ? y[1] : y
    
    ; 確保都是數字
    x := IsNumber(x) ? Integer(x) : 0
    y := IsNumber(y) ? Integer(y) : 0
    
    ; 創建資訊氣泡GUI
    BubbleGUI := Gui("+AlwaysOnTop -Caption +ToolWindow", "CoordinateBubble")
    BubbleGUI.BackColor := "0x2D2D30"
    BubbleGUI.MarginX := 10
    BubbleGUI.MarginY := 5
    
    ; 設定透明度
    WinSetTransparent(230, BubbleGUI.Hwnd)
    
    ; 創建文字顯示
    BubbleGUI.SetFont("s10 Bold", "Microsoft YaHei UI")
    
    if (info = "") {
        info := "座標: (" . x . ", " . y . ")"
    }
    
    TextControl := BubbleGUI.Add("Text", "c0xFFFFFF Center", info)
    
    ; 計算氣泡位置 (顯示在十字上方)
    bubbleX := x - 60
    bubbleY := y - 40
    
    ; 確保氣泡不超出螢幕邊界
    if (bubbleX < 0) bubbleX := 0
    if (bubbleY < 0) bubbleY := y + 30
    
    BubbleGUI.Show("x" . bubbleX . " y" . bubbleY . " AutoSize NoActivate")
    
    ; 2秒後自動銷毀
    SetTimer(() => BubbleGUI.Destroy(), -2000)
    
    return BubbleGUI
}

; 標準座標指示 (最常用)
ShowCoordinateIndicator(x, y, info := "") {
    ; 安全的參數類型轉換
    x := (IsObject(x) && x.Length > 0) ? x[1] : x
    y := (IsObject(y) && y.Length > 0) ? y[1] : y
    
    ; 確保都是數字
    x := IsNumber(x) ? Integer(x) : 0
    y := IsNumber(y) ? Integer(y) : 0
    
    ; 顯示動畫十字指示器
    CreateCrosshair(x, y, "0xFF0000", 30, 4, 220)
    
    ; 動畫效果：縮小並變色
    SetTimer(() => CreateCrosshair(x, y, "0xFFFF00", 25, 3, 200), -500)
    SetTimer(() => CreateCrosshair(x, y, "0x00FF00", 20, 2, 180), -1000)
    
    ; 顯示資訊氣泡
    if (info != "") {
        ShowCoordinateBubble(x, y, info)
    }
}

; 成功指示 (綠色)
ShowSuccessIndicator(x, y, message := "設定成功") {
    ; 安全的參數類型轉換
    x := (IsObject(x) && x.Length > 0) ? x[1] : x
    y := (IsObject(y) && y.Length > 0) ? y[1] : y
    
    ; 確保都是數字
    x := IsNumber(x) ? Integer(x) : 0
    y := IsNumber(y) ? Integer(y) : 0
    
    CreateCrosshair(x, y, "0x00FF00", 30, 4, 200)
    ShowCoordinateBubble(x, y, message)
}

; 錯誤指示 (紅色閃爍)
ShowErrorIndicator(x, y, message := "設定失敗") {
    ; 安全的參數類型轉換
    x := (IsObject(x) && x.Length > 0) ? x[1] : x
    y := (IsObject(y) && y.Length > 0) ? y[1] : y
    
    ; 確保都是數字
    x := IsNumber(x) ? Integer(x) : 0
    y := IsNumber(y) ? Integer(y) : 0
    
    ; 紅色閃爍效果
    CreateCrosshair(x, y, "0xFF0000", 35, 5, 255)
    SetTimer(() => DestroyCrosshair(), -300)
    SetTimer(() => CreateCrosshair(x, y, "0xFF0000", 30, 4, 200), -400)
    SetTimer(() => DestroyCrosshair(), -700)
    SetTimer(() => CreateCrosshair(x, y, "0xFF0000", 25, 3, 150), -800)
    
    ShowCoordinateBubble(x, y, message)
}

; ========================== Win+C 座標定位功能 ==========================

; 座標定位功能 (Win + C)
座標定位功能(*) {
    ; 🎮 第一步：激活遊戲視窗，確保座標正確
    try {
        ; 嘗試激活流亡黯道遊戲視窗
        if (WinExist("Path of Exile")) {
            WinActivate("Path of Exile")
            Sleep(100)  ; 等待視窗激活
        } else if (WinExist("Path of Exile 2")) {
            WinActivate("Path of Exile 2")
            Sleep(100)  ; 等待視窗激活
        } else {
            ; 沒有找到遊戲視窗，顯示提示
            ShowToolTip("❌ 未找到流亡黯道遊戲視窗！`n請確保遊戲正在運行", 4000, 1)
            return
        }
    } catch {
        ShowToolTip("❌ 激活遊戲視窗失敗！", 3000, 1)
        return
    }
    
    ; 🎯 第二步：確認遊戲視窗為活躍狀態後，抓取座標
    if (檢查遊戲視窗()) {
        ; 獲取當前滑鼠位置和顏色（現在確保是遊戲內的座標）
        MouseGetPos(&thisPosX, &thisPosY)
        colorabc := PixelGetColor(thisPosX, thisPosY)
        
        ; 確保座標是數字類型
        thisPosX := Integer(thisPosX)
        thisPosY := Integer(thisPosY)
        
        ; 創建美化的GUI面板（會自動處理十字準心）
        CreateCoordinateGUI(thisPosX, thisPosY, colorabc)
    } else {
        ShowToolTip("❌ 請在遊戲視窗中使用 Win+C 功能！", 3000, 1)
    }
}

; 創建Win+C偵測點抓取GUI
CreateCoordinateGUI(posX, posY, color) {
    global CoordGUI
    
    ; 如果已存在GUI，先關閉並清理
    try {
        if (CoordGUI) {
            DestroyCrosshair()  ; 清理舊的十字準心
            CoordGUI.Destroy()  ; 關閉舊GUI
            Sleep(50)  ; 短暫延遲確保清理完成
        }
    } catch {
        ; 忽略關閉錯誤，繼續創建新GUI
    }
    
    ; 安全的參數類型轉換
    posX := (IsObject(posX) && posX.Length > 0) ? posX[1] : posX
    posY := (IsObject(posY) && posY.Length > 0) ? posY[1] : posY
    
    ; 確保都是數字
    posX := IsNumber(posX) ? Integer(posX) : 0
    posY := IsNumber(posY) ? Integer(posY) : 0
    
    ; 🎯 創建新的十字準心指示器（在新位置）
    CreateCrosshair(posX, posY, "0xFF0000", 30, 4, 220, false)  ; autoClose = false
    
    ; 創建GUI - 調整尺寸以容納狀態顯示
    CoordGUI := Gui("+Resize +MaximizeBox", "🎯 Win+C 偵測點記錄工具 - Sid流亡工具箱")
    CoordGUI.BackColor := "0x2D2D30"
    CoordGUI.MarginX := 20
    CoordGUI.MarginY := 20
    
    ; 設定字體
    CoordGUI.SetFont("s14 Bold", "Microsoft YaHei UI")
    
    ; 標題區域
    TitleText := CoordGUI.Add("Text", "x20 y20 w720 h50 Center c0xFFFFFF", "🎯 Win+C 偵測點座標記錄工具")
    TitleText.SetFont("s20 Bold")
    
    ; 當前座標信息區域
    CoordGUI.SetFont("s12", "Microsoft YaHei UI")
    InfoGroup := CoordGUI.Add("GroupBox", "x20 y80 w720 h100 c0xC0C0C0", "📍 當前座標資訊")
    InfoGroup.SetFont("s14 Bold")
    
    CoordGUI.SetFont("s12", "Consolas")
    CoordText := CoordGUI.Add("Text", "x35 y110 w700 h25 c0x00FF00", "座標位置: (" . posX . ", " . posY . ")")
    ColorText := CoordGUI.Add("Text", "x35 y140 w700 h25 c0x00CCFF", "顏色代碼: 0x" . Format("{:06X}", color))
    
    ; 偵測點設置狀態顯示區域
    CoordGUI.SetFont("s12", "Microsoft YaHei UI")
    StatusGroup := CoordGUI.Add("GroupBox", "x20 y190 w720 h180 c0xC0C0C0", "📋 偵測點設置狀態")
    StatusGroup.SetFont("s14 Bold")
    
    CoordGUI.SetFont("s11", "Microsoft YaHei UI")
    ; 檢查偵測點設置狀態
    偵測點1狀態 := (顏色1_X != "error" && 顏色1_Y != "error") ? "✅ 已設置" : "❌ 未設置"
    偵測點2狀態 := (顏色2_X != "error" && 顏色2_Y != "error") ? "✅ 已設置" : "❌ 未設置"
    偵測點3狀態 := (顏色3_X != "error" && 顏色3_Y != "error") ? "✅ 已設置" : "❌ 未設置"
    偵測點4狀態 := (顏色4_X != "error" && 顏色4_Y != "error") ? "✅ 已設置" : "❌ 未設置"
    偵測點5狀態 := (顏色5_X != "error" && 顏色5_Y != "error") ? "✅ 已設置" : "❌ 未設置"
    偵測點6狀態 := (顏色6_X != "error" && 顏色6_Y != "error") ? "✅ 已設置" : "❌ 未設置"
    偵測點7狀態 := (顏色7_X != "error" && 顏色7_Y != "error") ? "✅ 已設置" : "❌ 未設置"
    偵測點8狀態 := (顏色8_X != "error" && 顏色8_Y != "error") ? "✅ 已設置" : "❌ 未設置"
    偵測點9狀態 := (顏色9_X != "error" && 顏色9_Y != "error") ? "✅ 已設置" : "❌ 未設置"
    
    ; 狀態顯示 - 左列（必須+建議） - 增加文字高度和寬度
    CoordGUI.Add("Text", "x35 y220 w240 h18 c0xFFD700", "🌍  場景偵測點 (必須):")
    偵測點1狀態顏色 := (偵測點1狀態 = "✅ 已設置") ? "0x00FF00" : "0xFF6666"
    CoordGUI.Add("Text", "x280 y220 w90 h18 c" . 偵測點1狀態顏色, 偵測點1狀態)
    
    CoordGUI.Add("Text", "x35 y242 w240 h18 c0x9E9E9E", "💬  對話框1偵測 (必須):")
    偵測點2狀態顏色 := (偵測點2狀態 = "✅ 已設置") ? "0x00FF00" : "0xFF6666"
    CoordGUI.Add("Text", "x280 y242 w90 h18 c" . 偵測點2狀態顏色, 偵測點2狀態)
    
    CoordGUI.Add("Text", "x35 y264 w240 h18 c0x9E9E9E", "💭  對話框2偵測 (必須):")
    偵測點3狀態顏色 := (偵測點3狀態 = "✅ 已設置") ? "0x00FF00" : "0xFF6666"
    CoordGUI.Add("Text", "x280 y264 w90 h18 c" . 偵測點3狀態顏色, 偵測點3狀態)
    
    CoordGUI.Add("Text", "x35 y286 w240 h18 c0xFF5722", "🩸  血球池偵測點 (推薦):")
    偵測點4狀態顏色 := (偵測點4狀態 = "✅ 已設置") ? "0x00FF00" : "0xFF6666"
    CoordGUI.Add("Text", "x280 y286 w90 h18 c" . 偵測點4狀態顏色, 偵測點4狀態)
    
    CoordGUI.Add("Text", "x35 y308 w240 h18 c0x0a9aee", "🔮  魔球偵測點 :")
    偵測點5狀態顏色 := (偵測點5狀態 = "✅ 已設置") ? "0x00FF00" : "0xFF6666"
    CoordGUI.Add("Text", "x280 y308 w90 h18 c" . 偵測點5狀態顏色, 偵測點5狀態)
    
    ; 狀態顯示 - 右列（進階+選用） - 增加文字高度和寬度
    CoordGUI.Add("Text", "x395 y220 w250 h18 c0x35e469", "�  血條偵測點 :")
    偵測點6狀態顏色 := (偵測點6狀態 = "✅ 已設置") ? "0x00FF00" : "0xFF6666"
    CoordGUI.Add("Text", "x650 y220 w90 h18 c" . 偵測點6狀態顏色, 偵測點6狀態)
    
    CoordGUI.Add("Text", "x395 y242 w250 h18 c0x3ab380", "🏠  返角偵測點 :")
    偵測點7狀態顏色 := (偵測點7狀態 = "✅ 已設置") ? "0x00FF00" : "0xFF6666"
    CoordGUI.Add("Text", "x650 y242 w90 h18 c" . 偵測點7狀態顏色, 偵測點7狀態)
    
    CoordGUI.Add("Text", "x395 y264 w250 h18 c0xc3d4dd", "⚡  穿透偵測點 :")
    偵測點8狀態顏色 := (偵測點8狀態 = "✅ 已設置") ? "0x00FF00" : "0xFF6666"
    CoordGUI.Add("Text", "x650 y264 w90 h18 c" . 偵測點8狀態顏色, 偵測點8狀態)
    
    CoordGUI.Add("Text", "x395 y286 w250 h18 c0xe4cdc5", "�  穿透返角點 :")
    偵測點9狀態顏色 := (偵測點9狀態 = "✅ 已設置") ? "0x00FF00" : "0xFF6666"
    CoordGUI.Add("Text", "x650 y286 w90 h18 c" . 偵測點9狀態顏色, 偵測點9狀態)
        
    ; 功能可用性分析 - 調整位置和寬度
    必須偵測點完成 := (偵測點1狀態 = "✅ 已設置") && (偵測點2狀態 = "✅ 已設置") && (偵測點3狀態 = "✅ 已設置")
    建議偵測點完成 := (偵測點4狀態 = "✅ 已設置") || (偵測點5狀態 = "✅ 已設置") || (偵測點6狀態 = "✅ 已設置") || (偵測點7狀態 = "✅ 已設置")
    進階偵測點完成 := (偵測點8狀態 = "✅ 已設置") || (偵測點9狀態 = "✅ 已設置")
    
    if (必須偵測點完成) {
        CoordGUI.Add("Text", "x35 y335 w350 h18 c0x00FF00", "🟢 基礎功能：可使用")
    } else {
        CoordGUI.Add("Text", "x35 y335 w350 h18 c0xFF6666", "🚨 基礎功能：需設置場景偵測點(1)、對話框1偵測(2)和對話框2偵測(3)")
    }
    
    if (建議偵測點完成) {
        CoordGUI.Add("Text", "x395 y335 w345 h18 c0x00FF00", "🔵 智能監控：可使用")
    } else {
        CoordGUI.Add("Text", "x395 y335 w345 h18 c0xFF6666", "🟡 智能監控：建議設置更多偵測點")
    }
    
    if (進階偵測點完成) {
        CoordGUI.Add("Text", "x35 y357 w350 h18 c0x00FF00", "🔥 進階功能：可使用")
    } else {
        CoordGUI.Add("Text", "x35 y357 w350 h18 c0xFF6666", "⚪ 進階功能：設置穿透偵測點以啟用")
    }
    
    CoordGUI.SetFont("s12 Bold", "Microsoft YaHei UI")
    
    ; 偵測點代碼說明區域
    CoordGUI.SetFont("s12", "Microsoft YaHei UI")
    DetectGroup := CoordGUI.Add("GroupBox", "x20 y385 w720 h200 c0xC0C0C0", "🎮 偵測點代碼說明")
    DetectGroup.SetFont("s14 Bold")
    
    CoordGUI.SetFont("s11", "Microsoft YaHei UI")
    ; 代碼說明 - 整齊排序，專注代號用途
    CoordGUI.Add("Text", "x35 y415 w680 h20 c0xC0C0C0", "1 = 場景偵測點 (遊戲狀態判斷)")
    CoordGUI.Add("Text", "x35 y437 w680 h20 c0xC0C0C0", "2 = Enter對話框(1)黑色域")
    CoordGUI.Add("Text", "x35 y459 w680 h20 c0xC0C0C0", "3 = Enter對話框(2)黑色域")
    CoordGUI.Add("Text", "x35 y481 w680 h20 c0xC0C0C0", "4 = 左下血球池偵測點")
    CoordGUI.Add("Text", "x35 y503 w680 h20 c0xC0C0C0", "5 = 右下魔球偵測點")
    CoordGUI.Add("Text", "x35 y525 w680 h20 c0xC0C0C0", "6 = 人物上方血條偵測點 (抓取空血顏色，越接近滿血=提早觸發)")
    CoordGUI.Add("Text", "x35 y547 w680 h20 c0xC0C0C0", "7 = 人物上方血條返角偵測點")
    CoordGUI.Add("Text", "x35 y569 w680 h20 c0xC0C0C0", "8 = 混傷穿透ES血條偵測點")
    CoordGUI.Add("Text", "x35 y591 w680 h20 c0xC0C0C0", "9 = 混傷穿透ES血條返角偵測點")
    
    CoordGUI.SetFont("s11", "Microsoft YaHei UI")
    CoordGUI.Add("Text", "x35 y615 w700 h22 c0xdbee2c", "💡 提示：請將滑鼠移動到需抓取的座標，再次使用 Win+C ! (紅十字為當前抓取到的座標)")

    ; 輸入區域 - 調整位置
    CoordGUI.SetFont("s12", "Microsoft YaHei UI")
    InputGroup := CoordGUI.Add("GroupBox", "x20 y645 w720 h100 c0xC0C0C0", "⌨️ 偵測點代號輸入")
    InputGroup.SetFont("s14 Bold")
    
    CoordGUI.SetFont("s12", "Microsoft YaHei UI")
    CoordGUI.Add("Text", "x35 y675 w200 h25 c0xFFFFFF", "請輸入偵測點代號:")
    
    ; 創建輸入框 - 添加 Number 選項限制只能輸入數字
    global CoordInput
    CoordInput := CoordGUI.Add("Edit", "x240 y673 w100 h30 Center c0x000000 Background0xFFFFFF Number")
    CoordInput.SetFont("s14 Bold", "Consolas")
    
    ; 輸入限制 - 只允許1-9（移除T選項）
    CoordInput.OnEvent("Change", (*) => ValidateInput())
    
    CoordGUI.Add("Text", "x350 y675 w360 h25 c0xC0C0C0", "有效輸入: 1-9")
    
    ; 按鈕區域 - 調整位置
    CoordGUI.SetFont("s12 Bold", "Microsoft YaHei UI")
    ConfirmBtn := CoordGUI.Add("Button", "x250 y765 w120 h40 c0xFFFFFF Background0x4CAF50 Default", "✅ 確定")
    CancelBtn := CoordGUI.Add("Button", "x390 y765 w120 h40 c0xFFFFFF Background0xF44336", "❌ 取消")
    
    ; 按鈕事件
    ConfirmBtn.OnEvent("Click", (*) => ProcessCoordinateInput(posX, posY, color, CoordGUI))
    CancelBtn.OnEvent("Click", (*) => CloseCoordGUI())
    
    ; ESC 鍵關閉，Enter 鍵確認
    CoordGUI.OnEvent("Escape", CloseCoordGUI)
    CoordGUI.OnEvent("Close", CloseCoordGUIWithHotkey)
    
    ; 添加按鍵處理 - 將參數保存到全局變量中以供按鍵處理使用
    global CurrentCoordData := {posX: posX, posY: posY, color: color, gui: CoordGUI}
    
    ; 設置 Enter 熱鍵確認
    try {
        Hotkey("Enter", HandleCoordEnterKey, "On")
    } catch {
        ; 如果熱鍵設置失敗，忽略錯誤
    }
    
    ; 顯示GUI - 擴大視窗尺寸以適應新內容
    CoordGUI.Show("w760 h825")
    
    ; 自動聚焦到輸入框
    CoordInput.Focus()
}

; 處理座標輸入的 Enter 鍵
HandleCoordEnterKey(*) {
    global CurrentCoordData
    
    ; 檢查是否有活動的座標GUI
    if (IsObject(CurrentCoordData) && IsObject(CurrentCoordData.gui)) {
        ProcessCoordinateInput(CurrentCoordData.posX, CurrentCoordData.posY, CurrentCoordData.color, CurrentCoordData.gui)
    }
}

; 關閉座標GUI並清理十字準心和熱鍵
CloseCoordGUIWithHotkey(*) {
    global CoordGUI
    
    ; 移除 Enter 熱鍵
    try {
        Hotkey("Enter", "Off")
    } catch {
        ; 忽略錯誤
    }
    
    DestroyCrosshair()  ; 關閉十字準心
    if (CoordGUI) {
        CoordGUI.Destroy()
    }
}

; 關閉座標GUI並清理十字準心
CloseCoordGUI(*) {
    global CoordGUI
    DestroyCrosshair()  ; 關閉十字準心
    if (CoordGUI) {
        CoordGUI.Destroy()
    }
}

; Win+C輸入驗證 - 只允許1-9，不能為空
ValidateInput(*) {
    global CoordInput
    
    currentText := CoordInput.Text
    if (currentText = "") {
        return
    }
    
    ; 檢查是否在1-9範圍內
    inputNum := Integer(currentText)
    if (inputNum < 1 || inputNum > 9) {
        ; 如果不在範圍內，清空輸入
        CoordInput.Text := ""
        ShowToolTip("❌ 請輸入有效的偵測點代號 (1-9)", 2000, 1)
    }
}

; 過濾有效字符（只保留數字和英文字母）
FilterValidChars(input) {
    result := ""
    Loop Parse, input {
        char := A_LoopField
        charCode := Ord(char)
        ; 只保留數字(0-9)和英文字母(A-Z, a-z)
        ; 0-9: ASCII 48-57, A-Z: ASCII 65-90, a-z: ASCII 97-122
        if (charCode >= 48 && charCode <= 57) || (charCode >= 65 && charCode <= 90) || (charCode >= 97 && charCode <= 122) {
            result .= char
        }
    }
    return result
}

; 處理座標輸入
ProcessCoordinateInput(posX, posY, color, parentGui) {
    global CoordInput

    ; 安全的參數類型轉換
    posX := (IsObject(posX) && posX.Length > 0) ? posX[1] : posX
    posY := (IsObject(posY) && posY.Length > 0) ? posY[1] : posY

    ; 確保都是數字
    posX := IsNumber(posX) ? Integer(posX) : 0
    posY := IsNumber(posY) ? Integer(posY) : 0

    ; 檢查 CoordInput 控件是否還存在
    global CoordInput
    if (!IsObject(CoordInput)) {
        return  ; 如果控件已被銷毀，直接返回
    }
    
    ColorID := ""
    try {
        ColorID := CoordInput.Text
    } catch {
        return  ; 如果無法獲取文本，直接返回
    }

    ; 強化的防呆機制 - 檢查輸入是否有效
    if (ColorID = "") {
        try {
            MsgBox("請輸入有效的偵測點代號！必須輸入 1-9 之間的數字", "輸入錯誤", 0x10)
            CoordInput.Focus()
        } catch {
            ; 如果無法操作控件，忽略錯誤
        }
        return
    }

    ; 檢查是否為有效數字
    if (!IsInteger(ColorID) || ColorID < 1 || ColorID > 9) {
        try {
            MsgBox("請輸入正確的代號！有效輸入範圍: 1-9", "輸入錯誤", 0x10)
            CoordInput.Text := ""
            CoordInput.Focus()
        } catch {
            ; 如果無法操作控件，忽略錯誤
        }
        return
    }

    ; 關閉GUI並清理十字準心
    DestroyCrosshair()  ; 先關閉舊的十字準心
    parentGui.Destroy()
    
    ; 使用固定配置檔案
    配置檔案 := CONFIG_FILE
    
    ; 檢查輸入是否為 1-9 的數字
    if (IsInteger(ColorID) && ColorID >= 1 && ColorID <= 9) {
        ; 將所有參數強制轉換為字串以避免陣列問題
        座標X字串 := "" . posX
        座標Y字串 := "" . posY
        顏色字串 := "" . color
        配置檔案字串 := "" . 配置檔案
        
        ; 座標名稱對應 - 直接使用字串
        if (ColorID = 1) {
            X鍵名 := "顏色1_X"
            Y鍵名 := "顏色1_Y"
            C鍵名 := "顏色1_C"
        } else if (ColorID = 2) {
            X鍵名 := "顏色2_X"
            Y鍵名 := "顏色2_Y"
            C鍵名 := "顏色2_C"
        } else if (ColorID = 3) {
            X鍵名 := "顏色3_X"
            Y鍵名 := "顏色3_Y"
            C鍵名 := "顏色3_C"
        } else if (ColorID = 4) {
            X鍵名 := "顏色4_X"
            Y鍵名 := "顏色4_Y"
            C鍵名 := "顏色4_C"
        } else if (ColorID = 5) {
            X鍵名 := "顏色5_X"
            Y鍵名 := "顏色5_Y"
            C鍵名 := "顏色5_C"
        } else if (ColorID = 6) {
            X鍵名 := "顏色6_X"
            Y鍵名 := "顏色6_Y"
            C鍵名 := "顏色6_C"
        } else if (ColorID = 7) {
            X鍵名 := "顏色7_X"
            Y鍵名 := "顏色7_Y"
            C鍵名 := "顏色7_C"
        } else if (ColorID = 8) {
            X鍵名 := "顏色8_X"
            Y鍵名 := "顏色8_Y"
            C鍵名 := "顏色8_C"
        } else if (ColorID = 9) {
            X鍵名 := "顏色9_X"
            Y鍵名 := "顏色9_Y"
            C鍵名 := "顏色9_C"
        }
        
        ; 儲存座標和顏色 - 使用最直接的方式
        try {
            IniWrite(座標X字串, 配置檔案字串, "顏色座標", X鍵名)
            IniWrite(座標Y字串, 配置檔案字串, "顏色座標", Y鍵名)
            IniWrite(顏色字串, 配置檔案字串, "顏色座標", C鍵名)
            
            ; 重新讀取座標
            讀取顏色座標()
            
            ; 🎯 顯示成功指示器
            ShowSuccessIndicator(posX, posY, "座標 " . ColorID . " 設定完成！")
            
            ShowToolTip("✅ 座標 " . ColorID . " 設定完成！`n位置：(" . posX . ", " . posY . ")`n顏色：" . color, 3000, 1)
            
            ; 🎯 檢查是否為引導模式，如果是則自動返回設定精靈
            if (設定引導模式) {
                ; 延遲一下讓用戶看到成功消息
                SetTimer((*) => 取消座標設定引導(), -2000)
            }
        } catch Error as err {
            ; 🎯 顯示錯誤指示器
            ShowErrorIndicator(posX, posY, "座標儲存失敗")
            ShowToolTip("❌ 儲存座標失敗：" . err.Message, 3000, 1)
        }
    }
}

; 讀取顏色座標
讀取顏色座標() {
    global 顏色1_X, 顏色1_Y, 顏色1_C, 顏色2_X, 顏色2_Y, 顏色2_C, 顏色3_X, 顏色3_Y, 顏色3_C
    global 顏色4_X, 顏色4_Y, 顏色4_C, 顏色5_X, 顏色5_Y, 顏色5_C, 顏色6_X, 顏色6_Y, 顏色6_C
    global 顏色7_X, 顏色7_Y, 顏色7_C, 顏色8_X, 顏色8_Y, 顏色8_C, 顏色9_X, 顏色9_Y, 顏色9_C
    
    ; 使用固定配置檔案
    配置檔案 := CONFIG_FILE
    
    try {
        Loop 9 {
            ; 讀取 X 座標
            變數名X := "顏色" . A_Index . "_X"
            %變數名X% := IniRead(配置檔案, "顏色座標", 變數名X, "error")
            
            ; 讀取 Y 座標
            變數名Y := "顏色" . A_Index . "_Y"
            %變數名Y% := IniRead(配置檔案, "顏色座標", 變數名Y, "error")
            
            ; 讀取顏色
            變數名C := "顏色" . A_Index . "_C"
            %變數名C% := IniRead(配置檔案, "顏色座標", 變數名C, "error")
        }
    } catch Error as err {
        ; 讀取失敗時保持預設值
    }
}

; 讀取血球魔力球設定
讀取血球魔力球設定_舊版() {
    global 偵測血球池打勾紀錄, 偵測魔球喝水打勾紀錄, 藥劑按鍵2, 藥劑按鍵4, 偵測喝水間隔, ToolTipOff
    
    try {
        偵測血球池打勾紀錄 := IniRead(CONFIG_FILE, "偵測喝水數據", "偵測血球池打勾紀錄", "-checked")
        偵測魔球喝水打勾紀錄 := IniRead(CONFIG_FILE, "偵測喝水數據", "偵測魔球喝水打勾紀錄", "-checked")
        藥劑按鍵2 := IniRead(CONFIG_FILE, "偵測喝水數據", "藥劑按鍵2", "error")  ; 魔力藥劑
        藥劑按鍵4 := IniRead(CONFIG_FILE, "偵測喝水數據", "藥劑按鍵4", "error")  ; 血球藥劑
        偵測喝水間隔 := IniRead(CONFIG_FILE, "偵測喝水數據", "偵測喝水間隔", "500")
        
        ; 讀取工具提示開關
        工具提示狀態 := IniRead(CONFIG_FILE, "偵測喝水數據", "工具提示開關", "開啟")
        ToolTipOff := (工具提示狀態 == "開啟") ? 0 : 1
        
    } catch Error as err {
        ; 讀取失敗時保持預設值
    }
}

; ========================== 文字模式偵測功能 ==========================

; Enter 偵測對話框功能
Enter偵測對話框(*) {
    global 顏色2_X, 顏色2_Y, 顏色3_X, 顏色3_Y, Enter除錯提醒次數, Toolbutton
    
    ; 檢查是否已設定偵測對話框座標
    if (顏色2_X = "error" || 顏色2_Y = "error" || 顏色3_X = "error" || 顏色3_Y = "error") {
        if (Enter除錯提醒次數 = 0) {
            顯示對話框設定指導()
            Enter除錯提醒次數 := 1
            IniWrite(Enter除錯提醒次數, CONFIG_FILE, "系統設定", "Enter除錯提醒次數")
        } else {
            ; 🔒 安全模式：如果使用者之前選擇了稍後設定，提供溫和提醒
            ShowToolTip("💡 提醒：對話框偵測功能需要設定座標才能正常運作`n" .
                       "按 Win+C 可快速設定偵測點", 4000, 1)
        }
        return  ; 🛡️ 重要：當座標未設定時，直接返回避免異常
    } else {
        ; 額外安全檢查：確保啟動偵測成功
        if (Toolbutton = 0) {
            Toolbutton := 1
            ShowToolTip("已切換為文字模式", 2000, 2)
            ; 安全啟動偵測，如果失敗則回退
            偵測啟動成功 := 啟動對話框偵測()
            if (偵測啟動成功) {
                ; 藥劑系統已移除，不需要暫停
            } else {
                ; 如果啟動失敗，恢復遊戲模式
                Toolbutton := 0
                ShowToolTip("⚠️ 對話框偵測啟動失敗，已恢復遊戲模式", 3000, 1)
            }
        } else {
            Toolbutton := 0
            ShowToolTip("已切換為遊戲模式", 2000, 2)
            停止對話框偵測()
        }
    }
}

; Ctrl+F 偵測
Ctrl_F偵測(*) {
    global Toolbutton
    
    if (Toolbutton = 0) {
        Toolbutton := 1
        ShowToolTip("偵測到使用 Ctrl + F，已切換為文字模式", 2000, 2)
        ; 藥劑系統已移除，不需要暫停
    }
}

; 監測背包狀態 - 靜默監測I鍵使用
監測背包狀態(*) {
    global openI, Toolbutton
    
    ; 只在遊戲模式下監測背包狀態
    if (Toolbutton = 0) {
        ; 切換背包開關狀態 (0 = 關閉, 1 = 開啟)
        openI := (openI = 0) ? 1 : 0
        
        ; 🔧 除錯模式：顯示背包狀態（可選啟用）
        ; ShowToolTip("🎒 背包狀態: " . (openI = 1 ? "開啟" : "關閉"), 1500, 5)
    }
}

; 監測滑鼠左鍵 - 文字模式智能切換判定
監測滑鼠左鍵(*) {
    global Toolbutton, 滑鼠開始時間
    
    ; 只在文字模式下監測滑鼠左鍵點擊
    if (Toolbutton = 1) {
        ; 檢查是否點擊了遊戲區域（通過視窗標題判定）
        if (WinActive("Path of Exile") || WinActive("Path of Exile 2")) {
            ; 記錄按下時間，啟動滑鼠彈起監聽
            if (!滑鼠開始時間) {
                滑鼠開始時間 := A_TickCount
                HotKey("~*LButton Up", 滑鼠左鍵彈起處理, "On")
            }
        }
    }
}

; 滑鼠左鍵彈起處理 - 計算按壓時間決定是否切換模式
滑鼠左鍵彈起處理(*) {
    global Toolbutton, 滑鼠開始時間
    
    ; 關閉彈起監聽器
    try {
        HotKey("~*LButton Up", "Off")
    }
    
    ; 計算按壓時間長度
    if (滑鼠開始時間) {
        時間長度 := A_TickCount - 滑鼠開始時間
        
        ; 只有長按（≥100毫秒）才切換模式，避免誤觸
        if (時間長度 >= 100 && Toolbutton = 1) {
            Toolbutton := 0
            ShowToolTip("偵測左鍵長時間按壓，已切換為遊戲模式", 2000, 2)
            停止對話框偵測()
            
            ; 🔧 除錯模式：顯示按壓時間（可選啟用）
            ; ShowToolTip("🖱️ 按壓時間: " . 時間長度 . "ms", 1500, 6)
        }
        
        ; 重置計時變數
        滑鼠開始時間 := 0
    }
}

; 啟動對話框偵測
啟動對話框偵測() {
    global 顏色2_X, 顏色2_Y, 顏色3_X, 顏色3_Y
    
    ; 安全檢查：確保座標已正確設定
    if (顏色2_X = "error" || 顏色2_Y = "error" || 顏色3_X = "error" || 顏色3_Y = "error") {
        ShowToolTip("⚠️ 對話框偵測座標未設定，無法啟動偵測功能", 3000, 1)
        return false
    }
    
    ; 設置對話框偵測計時器
    try {
        SetTimer(偵測對話框1, 25, 5000)  ; 高優先級：UI偵測
        SetTimer(偵測對話框2, 25, 5000)  ; 高優先級：UI偵測
        return true
    } catch Error as err {
        ShowToolTip("❌ 啟動對話框偵測失敗: " . err.message, 3000, 1)
        return false
    }
}

; 停止對話框偵測
停止對話框偵測() {
    try {
        SetTimer(偵測對話框1, 0)
        SetTimer(偵測對話框2, 0)
    } catch {
    }
}

; ======================================================================================================
; 🎯 顏色偵測輔助函數
; ======================================================================================================

; 🔥 智能顏色比對函數 - 支援容錯範圍 (防止遊戲特效干擾)
顏色比對(當前顏色, 目標顏色, 容錯值 := 0) {
    ; 如果沒有指定容錯值，使用全域設定
    if (容錯值 <= 0) {
        容錯值 := 顏色容錯值
    }
    
    ; 如果容錯值為0，使用精確比對
    if (容錯值 == 0) {
        return (當前顏色 == 目標顏色)
    }
    
    ; RGB分量分解
    當前R := (當前顏色 >> 16) & 0xFF
    當前G := (當前顏色 >> 8) & 0xFF
    當前B := 當前顏色 & 0xFF
    
    目標R := (目標顏色 >> 16) & 0xFF
    目標G := (目標顏色 >> 8) & 0xFF
    目標B := 目標顏色 & 0xFF
    
    ; 檢查各分量是否在容錯範圍內
    R差值 := Abs(當前R - 目標R)
    G差值 := Abs(當前G - 目標G)
    B差值 := Abs(當前B - 目標B)
    
    return (R差值 <= 容錯值 && G差值 <= 容錯值 && B差值 <= 容錯值)
}

; ======================================================================================================
; 🔥 新增缺少的偵測功能實裝
; ======================================================================================================

; 偵測血條喝水 (CheckBloodDrink) - 監控血條變化自動喝水
偵測血條喝水() {
    try {
        global 顏色6_X, 顏色6_Y, 藥劑按鍵4, 偵測血條喝水打勾紀錄, Toolbutton
        
        if (WinActive("Path of Exile") || WinActive("Path of Exile 2")) {
            ; 🔍 檢查是否為文字輸入模式
            if (Toolbutton == 1) {
                return  ; 文字模式時停止偵測
            }
            
            if (偵測血條喝水打勾紀錄 == "+checked") {
                if (顏色6_X != "error" && 顏色6_Y != "error" && 藥劑按鍵4 != "error") {
                    
                    ; 🔥 偵測血條固定顏色 - 與使用者抓取的顏色完全匹配
                    當前顏色 := PixelGetColor(顏色6_X, 顏色6_Y)
                    
                    ; 🎯 使用容錯顏色比對 - 防止遊戲特效造成的顏色輕微變化
                    if (顏色比對(當前顏色, 顏色6_C)) {
                        static 上次喝血時間 := 0
                        當前時間 := A_TickCount
                        
                        ; 防止過於頻繁觸發 (2秒內只能喝一次)
                        if (當前時間 - 上次喝血時間 > 2000) {
                            Send("{" . 藥劑按鍵4 . "}")
                            上次喝血時間 := 當前時間
                            ShowToolTip("🩸 血條偵測: 自動喝血", 1000, 2)
                        }
                    }
                }
            }
        }
    } catch {
        ; 忽略偵測錯誤
    }
}

; 偵測血條返角 (CheckBloodReturn) - 血量極低時自動返回角色選單
; 🔥 重要：返角功能抓取的是"沒血量時的顏色"，與血球池不同
; 血球池抓取"有血量時的顏色"，顏色不匹配時喝水
; 血條返角抓取"沒血量時的顏色"，顏色匹配時返角
偵測血條返角() {
    try {
        global 顏色7_X, 顏色7_Y, 顏色7_C, 偵測血條返角打勾紀錄, Toolbutton
        
        ; 🎮 確保只在遊戲視窗活躍且非文字模式時運作
        if (WinActive("Path of Exile") || WinActive("Path of Exile 2")) {
            ; 🔍 檢查是否為文字輸入模式
            if (Toolbutton == 1) {
                return  ; 文字模式時停止偵測
            }
            
            if (偵測血條返角打勾紀錄 == "+checked") {
                if (顏色7_X != "error" && 顏色7_Y != "error") {
                    
                    當前顏色 := PixelGetColor(顏色7_X, 顏色7_Y)
                    
                    ; 🎯 當抓取的"沒血量顏色"出現時執行返角
                    if (顏色比對(當前顏色, 顏色7_C)) {
                        static 上次返角時間 := 0
                        當前時間 := A_TickCount
                        
                        ; 防止誤判 (1.5秒內只能返角一次)
                        if (當前時間 - 上次返角時間 > 1500) {
                            ; 🔥 執行返角動作 (只按一次ESC)
                            Send("{Escape}")
                            上次返角時間 := 當前時間
                        }
                    }
                }
            }
        }
    } catch {
        ; 忽略錯誤，繼續運行
    }
}

; 偵測血條穿透 (CheckBloodPierce) - 檢測穿透傷害並觸發防護
偵測血條穿透() {
    try {
        global 顏色8_X, 顏色8_Y, 顏色8_C, 偵測血條穿透打勾紀錄, Toolbutton
        
        if (WinActive("Path of Exile") || WinActive("Path of Exile 2")) {
            ; 🔍 檢查是否為文字輸入模式
            if (Toolbutton == 1) {
                return  ; 文字模式時停止偵測
            }
            
            if (偵測血條穿透打勾紀錄 == "+checked") {
                if (顏色8_X != "error" && 顏色8_Y != "error") {
                    
                    當前顏色 := PixelGetColor(顏色8_X, 顏色8_Y)
                    
                    ; 🎯 使用容錯顏色比對 - 防止遊戲特效造成的顏色輕微變化
                    if (顏色比對(當前顏色, 顏色8_C)) {
                        static 上次穿透時間 := 0
                        當前時間 := A_TickCount
                        
                        ; 防止過於頻繁觸發 (3秒內只能觸發一次)
                        if (當前時間 - 上次穿透時間 > 3000) {
                            ; 觸發防護技能 (通常是R鍵)
                            Send("{R}")
                            上次穿透時間 := 當前時間
                            ShowToolTip("⚡ 穿透偵測: 觸發防護", 1500, 2)
                        }
                    }
                }
            }
        }
    } catch {
        ; 忽略偵測錯誤
    }
}

; 穿透返角偵測 (CheckPierceReturn) - 穿透傷害嚴重時自動返角
偵測穿透返角() {
    try {
        global 顏色9_X, 顏色9_Y, 顏色9_C, 偵測穿透返角打勾紀錄, Toolbutton
        
        if (WinActive("Path of Exile") || WinActive("Path of Exile 2")) {
            ; 🔍 檢查是否為文字輸入模式
            if (Toolbutton == 1) {
                return  ; 文字模式時停止偵測
            }
            
            if (偵測穿透返角打勾紀錄 == "+checked") {
                if (顏色9_X != "error" && 顏色9_Y != "error") {
                    
                    當前顏色 := PixelGetColor(顏色9_X, 顏色9_Y)
                    
                    ; 🎯 使用容錯顏色比對 - 防止遊戲特效造成的顏色輕微變化
                    if (顏色比對(當前顏色, 顏色9_C)) {
                        static 上次穿透返角時間 := 0
                        當前時間 := A_TickCount
                        
                        ; 防止誤判 (8秒內只能返角一次)
                        if (當前時間 - 上次穿透返角時間 > 8000) {
                            Send("{T}")
                            上次穿透返角時間 := 當前時間
                            ShowToolTip("🔄 穿透返角: 傷害過高!", 3000, 1)
                        }
                    }
                }
            }
        }
    } catch {
        ; 忽略偵測錯誤
    }
}

; 偵測對話框1
偵測對話框1() {
    global 顏色2_X, 顏色2_Y, 顏色2_C, Toolbutton
    
    if (顏色2_X = "error" || 顏色2_Y = "error") {
        停止對話框偵測()
        ; 使用友善GUI取代冰冷警告
        ShowToolTip("⚠️ 對話框偵測點未設定，請設定座標2", 3000, 1)
        return
    }
    
    try {
        對話框1顏色 := PixelGetColor(Integer(顏色2_X), Integer(顏色2_Y))
        if (顏色比對(對話框1顏色, 顏色2_C)) {
            Toolbutton := 1  ; 變更為文字模式
            ShowToolTip("偵測到對話框1，變更為文字模式", 2000, 2)
            ; 藥劑系統已移除，不需要暫停
            SetTimer(偵測對話框1, 0)  ; 停止計時器
        } else {
            SetTimer(偵測對話框1, 0)  ; 停止計時器
        }
    } catch {
        SetTimer(偵測對話框1, 0)  ; 停止計時器
    }
}

; 偵測對話框2
偵測對話框2() {
    global 顏色3_X, 顏色3_Y, 顏色3_C, Toolbutton
    
    if (顏色3_X = "error" || 顏色3_Y = "error") {
        停止對話框偵測()
        ; 使用友善GUI取代冰冷警告
        ShowToolTip("⚠️ 對話框偵測點未設定，請設定座標3", 3000, 1)
        return
    }
    
    try {
        對話框2顏色 := PixelGetColor(Integer(顏色3_X), Integer(顏色3_Y))
        if (顏色比對(對話框2顏色, 顏色3_C)) {
            Toolbutton := 1  ; 變更為文字模式
            ShowToolTip("偵測到對話框2，變更為文字模式", 2000, 2)
            ; 藥劑系統已移除，不需要暫停
            SetTimer(偵測對話框2, 0)  ; 停止計時器
        } else {
            SetTimer(偵測對話框2, 0)  ; 停止計時器
        }
    } catch {
        SetTimer(偵測對話框2, 0)  ; 停止計時器
    }
}

; ======================================================================================================
; 🎯 POE智能撿取系統 (參考POE_Utility擴展功能)
; ======================================================================================================

; 智能撿取設定變數
global 智能拾取開關 := false
global 拾取目標顏色 := "0x640065"  ; 預設撊取顏色 (100, 0, 122)
global 拾取搜索範圍 := 0
global 拾取間隔時間 := 100
global 拾取最大距離 := 500

; 載入智能拾取設置
載入智能拾取設置() {
    try {
        ; 從INI文件讀取設定
        global 拾取目標顏色 := IniRead(CONFIG_FILE, "智能拾取設置", "拾取目標顏色", "0x640065")
        global 拾取搜索範圍 := Integer(IniRead(CONFIG_FILE, "智能拾取設置", "拾取搜索範圍", "0"))
        global 拾取間隔時間 := Integer(IniRead(CONFIG_FILE, "智能拾取設置", "拾取間隔時間", "100"))
        global 拾取最大距離 := Integer(IniRead(CONFIG_FILE, "智能拾取設置", "拾取最大距離", "500"))
        global 智能拾取開關 := (IniRead(CONFIG_FILE, "智能拾取設置", "智能拾取開關", "false") = "true")
    } catch {
        ; 如果讀取失敗，使用預設值
        global 拾取目標顏色 := "0x640065"
        global 拾取搜索範圍 := 0
        global 拾取間隔時間 := 100
        global 拾取最大距離 := 500
        global 智能拾取開關 := false
    }
}

; 在程式啟動時載入設置
載入智能拾取設置()

; F8 智能撿取功能 (完全鎖定F8鍵，防止觸發遊戲截圖)
F8:: {
    if (!WinActive("Path of Exile") && !WinActive("Path of Exile 2")) {
        return
    }
    
    ; 首次使用F8功能提示
    static 首次F8使用 := true
    if (首次F8使用) {
        首次F8使用 := false
        ShowInfo("🎯 歡迎使用F8智能拾取功能！`n使用 Shift+F8 設定拾取顏色和參數", 4000)
    }
    
    ; 檢查是否已設定拾取顏色
    if (!拾取目標顏色 || 拾取目標顏色 = "error") {
        ShowError("尚未設定拾取顏色！`n請先使用 Shift+F8 設定拾取顏色")
        return
    }
    
    if (智能拾取開關) {
        停止智能拾取()
    } else {
        開始智能拾取()
    }
}

; 開始智能拾取
開始智能拾取() {
    global 智能拾取開關
    智能拾取開關 := true
    ShowToolTip("🎯 智能撿取：已啟動", 2000, 1)
    SetTimer(執行智能拾取, 拾取間隔時間)
    
    ; 保存狀態到INI文件
    try {
        IniWrite("true", CONFIG_FILE, "智能拾取設置", "智能拾取開關")
    } catch {
        ; 忽略保存錯誤
    }
}

; 停止智能拾取
停止智能拾取() {
    global 智能拾取開關
    智能拾取開關 := false
    ShowToolTip("⏹️ 智能撿取：已停止", 2000, 1)
    SetTimer(執行智能拾取, 0)
    
    ; 保存狀態到INI文件
    try {
        IniWrite("false", CONFIG_FILE, "智能拾取設置", "智能拾取開關")
    } catch {
        ; 忽略保存錯誤
    }
}

; 執行智能拾取邏輯
執行智能拾取() {
    if (!智能拾取開關 || !WinActive("Path of Exile") && !WinActive("Path of Exile 2")) {
        return
    }
    
    try {
        ; 獲取遊戲視窗位置和大小
        WinGetClientPos(&winX, &winY, &winWidth, &winHeight, "A")
        
        ; 確保視窗大小有效
        if (winWidth <= 0 || winHeight <= 0) {
            return
        }
        
        ; 計算螢幕中心點
        centerX := winX + winWidth // 2
        centerY := winY + winHeight // 2
        
        ; 定義從中心點開始的搜索範圍
        searchRadius := 拾取最大距離  ; 使用拾取最大距離作為搜索半徑
        
        ; 計算搜索區域邊界（確保不超出遊戲視窗）
        searchLeft := Max(winX, centerX - searchRadius)
        searchTop := Max(winY, centerY - searchRadius)
        searchRight := Min(winX + winWidth - 1, centerX + searchRadius)
        searchBottom := Min(winY + winHeight - 1, centerY + searchRadius)
        
        ; 搜索目標顏色（以螢幕中心為起點的範圍）
        if (PixelSearch(&px, &py, searchLeft, searchTop, searchRight, searchBottom, 拾取目標顏色, 拾取搜索範圍)) {
            ; 確保找到的座標在視窗範圍內
            if (px >= winX && px <= winX + winWidth && py >= winY && py <= winY + winHeight) {
                ; 檢查距離是否合理（從中心點計算距離）
                distance := Sqrt((px - centerX)**2 + (py - centerY)**2)
                
                if (distance <= 拾取最大距離) {
                    ; 點擊撿取
                    Click(px, py)
                    Sleep(50)
                }
            }
        }
    } catch {
        ; 錯誤時靜默處理
    }
}

; ====== 智能拾取 GUI 驗證函數 ======

; 驗證函數：範圍 (0-5) - 接收控制項物件
ValidateRangeInput_Range(ctrl) {
    try {
        val := Integer(ctrl.Text)
    } catch {
        val := 0
    }
    if (val < 0) val := 0
    if (val > 5) val := 5
    ctrl.Text := val
}

; 驗證函數：間隔 (5-2000 ms) - 接收控制項物件
ValidateRangeInput_Interval(ctrl) {
    currentText := ctrl.Text
    
    ; 如果是空的，設為預設值
    if (currentText = "") {
        ctrl.Text := 100
        return
    }
    
    ; 檢查是否為有效數字
    if (!IsInteger(currentText)) {
        ctrl.Text := 100
        return
    }
    
    try {
        v := Integer(currentText)
        
        ; 只有在值明顯超出合理範圍時才修正
        if (v < 5) {
            ctrl.Text := 5
            ShowToolTip("⚠️ 拾取間隔最小值為 5ms", 2000, 1)
        } else if (v > 5000) {  ; 放寬上限到 5000ms
            ctrl.Text := 5000
            ShowToolTip("⚠️ 拾取間隔最大值為 5000ms", 2000, 1)
        }
        ; 如果在 5-5000 範圍內，完全不修改用戶輸入
    } catch {
        ; 如果無法轉換為整數，設為預設值
        ctrl.Text := 100
    }
}

; 驗證函數：距離 (0-1000 px) - 接收控制項物件
ValidateRangeInput_Distance(ctrl) {
    try {
        d := Integer(ctrl.Text)
    } catch {
        d := 0
    }
    if (d < 0) d := 0
    if (d > 1000) d := 1000
    ctrl.Text := d
}

; Shift+F8 智能拾取設置
+F8:: {
    顯示智能拾取設置GUI()
}

; 智能拾取設置GUI
顯示智能拾取設置GUI() {
    global
    
    ; 創建主GUI
    拾取設置GUI := Gui("+AlwaysOnTop", "🎯 智能拾取設置")
    拾取設置GUI.BackColor := "0xF0F8FF"
    拾取設置GUI.SetFont("s11", "Microsoft YaHei UI")

    ; 佈局常數
    leftMargin := 25
    rightMargin := 25
    guiWidth := 420
    contentWidth := guiWidth - leftMargin - rightMargin
    
    xLabel := leftMargin
    xInput := 150
    xBtn := 280
    wLabel := 120
    wInput := 110
    wBtn := 85
    
    yPos := 25
    lineHeight := 38
    sectionGap := 15

    ; === 標題區域 ===
    拾取設置GUI.Add("Text", "x" leftMargin " y" yPos " w" contentWidth " h35 Center", "🎯 智能拾取系統設置").SetFont("s15 Bold")
    yPos += 50

    ; === 狀態顯示區域 ===
    狀態文字 := 智能拾取開關 ? "🟢 已啟動" : "🔴 已停止"
    拾取設置GUI.Add("Text", "x" leftMargin " y" yPos " w" contentWidth " h30", "當前狀態: " . 狀態文字).SetFont("s11 Bold c0x0066CC")
    yPos += 45

    ; === 設置區域 ===
    ; 拾取顏色設置
    拾取設置GUI.Add("Text", "x" xLabel " y" yPos " w" wLabel " h25", "拾取顏色:")
    顏色輸入 := 拾取設置GUI.Add("Edit", "x" xInput " y" (yPos-2) " w" wInput " h25 ReadOnly", 拾取目標顏色)
    拾取設置GUI.Add("Button", "x" xBtn " y" (yPos-3) " w" wBtn " h27", "🎯 抓取").OnEvent("Click", 開始互動式顏色抓取)
    yPos += lineHeight

    ; 顏色容差設置
    拾取設置GUI.Add("Text", "x" xLabel " y" yPos " w" wLabel " h25", "顏色容差:")
    範圍輸入 := 拾取設置GUI.Add("Edit", "x" xInput " y" (yPos-2) " w60 h25 Number vRangeInput", 拾取搜索範圍)
    範圍輸入.OnEvent("LoseFocus", (*) => ValidateRangeInput_Range(範圍輸入))
    拾取設置GUI.Add("Text", "x" (xInput+70) " y" yPos " w150 h25 c0x666666", "(0-5，推薦2-3)")
    yPos += lineHeight

    ; 拾取間隔設置
    拾取設置GUI.Add("Text", "x" xLabel " y" yPos " w" wLabel " h25", "拾取間隔(ms):")
    間隔輸入 := 拾取設置GUI.Add("Edit", "x" xInput " y" (yPos-2) " w" wInput " h25 Number vIntervalInput", 拾取間隔時間)
    間隔輸入.OnEvent("LoseFocus", (*) => ValidateRangeInput_Interval(間隔輸入))
    拾取設置GUI.Add("Text", "x" (xInput+wInput+10) " y" yPos " w150 h25 c0x666666", "(5-5000，推薦100-500)")
    yPos += lineHeight

    ; 最大距離設置
    拾取設置GUI.Add("Text", "x" xLabel " y" yPos " w" wLabel " h25", "最大距離(像素):")
    距離輸入 := 拾取設置GUI.Add("Edit", "x" xInput " y" (yPos-2) " w" wInput " h25 Number vDistanceInput", 拾取最大距離)
    距離輸入.OnEvent("LoseFocus", (*) => ValidateRangeInput_Distance(距離輸入))
    yPos += lineHeight + sectionGap

    ; === 使用說明區域 ===
    拾取設置GUI.Add("Text", "x" leftMargin " y" yPos " w" contentWidth " h25", "💡 使用方法:").SetFont("s12 Bold c0x2E8B57")
    yPos += 30
    
    說明內容 := "1. 在物品過濾器中加上邊框顏色`n"
    說明內容 .= "2. 點擊【🎯 抓取】按鈕進入顏色抓取模式`n"
    說明內容 .= "3. 移動滑鼠到目標顏色位置，按 Enter 確認`n"
    說明內容 .= "4. 按 F8 開啟或關閉智能拾取功能"
    
    拾取設置GUI.Add("Text", "x" (leftMargin+20) " y" yPos " w" (contentWidth-20) " h100", 說明內容).SetFont("s10")
    yPos += 115

    ; === 按鈕區域 ===
    btnY := yPos
    btnSpacing := 110
    btn1X := (guiWidth - btnSpacing * 3) // 2 + 10
    
    拾取設置GUI.Add("Button", "x" btn1X " y" btnY " w90 h35", "✅ 保存").OnEvent("Click", 保存拾取設置)
    拾取設置GUI.Add("Button", "x" (btn1X + btnSpacing) " y" btnY " w90 h35", "🧪 測試").OnEvent("Click", 測試拾取功能)
    拾取設置GUI.Add("Button", "x" (btn1X + btnSpacing * 2) " y" btnY " w90 h35", "❌ 關閉").OnEvent("Click", (*) => 拾取設置GUI.Destroy())

    ; 設置全域變數
    global 顏色抓取中 := false
    global 顏色抓取計時器 := ""
    global 當前拾取設置GUI := 拾取設置GUI


    global 當前顏色輸入控制項 := 顏色輸入
    
    ; 顯示GUI並激活為前景視窗
    拾取設置GUI.Show("w" guiWidth " h" (btnY + 60))
    
    ; 確保GUI成為活動視窗
    try {
        WinActivate(拾取設置GUI.Hwnd)
        WinSetAlwaysOnTop(true, 拾取設置GUI.Hwnd)
        Sleep(100)  ; 短暫延遲確保激活完成
        WinSetAlwaysOnTop(false, 拾取設置GUI.Hwnd)
    } catch {
        ; 如果激活失敗，忽略錯誤
    }

    ; 添加ESC鍵關閉功能
    Hotkey("Escape", 關閉拾取設置GUI, "On")
    
    ; 當GUI銷毀時移除熱鍵
    拾取設置GUI.OnEvent("Close", (*) => Hotkey("Escape", "Off"))

    ; ====== 事件處理函數 ======
    
    開始互動式顏色抓取(*) {
        global 顏色抓取中, 顏色抓取計時器, 拾取設置GUI
        
        if (顏色抓取中) {
            停止顏色抓取()
            return
        }
        
        ; 隱藏主GUI讓使用者專心抓取
        try {
            拾取設置GUI.Hide()
        } catch {
            ; 忽略隱藏錯誤
        }
        
        顏色抓取中 := true
        ShowToolTip("🎯 顏色抓取模式已啟動`n移動滑鼠到目標顏色位置`n按 Enter 確認，按 Esc 取消", 3000, 1)
        
        顏色抓取計時器 := SetTimer(更新顏色監控, 200)
        
        Hotkey("Enter", 確認顏色抓取, "On")
        Hotkey("Escape", 取消顏色抓取, "On")
    }
    
    保存拾取設置(*) {
        ; 保存顏色設置
        global 拾取目標顏色 := 顏色輸入.Text
        
        ; 驗證並限制容差值 (0-5)
        tolerance := Integer(範圍輸入.Text)
        if (!IsNumber(範圍輸入.Text) || tolerance < 0 || tolerance > 5) {
            ShowToolTip("❌ 顏色容差必須是 0-5 之間的數字", 3000, 1)
            return
        }
        global 拾取搜索範圍 := tolerance
        
        ; 驗證拾取間隔 (必須是數字)
        interval := Integer(間隔輸入.Text)
        if (!IsNumber(間隔輸入.Text) || interval <= 0) {
            ShowToolTip("❌ 拾取間隔必須是正整數", 3000, 1)
            return
        }
        global 拾取間隔時間 := interval
        
        ; 保存其他設置
        global 拾取最大距離 := Integer(距離輸入.Text)
        
        ; 保存到INI文件
        try {
            IniWrite(拾取目標顏色, CONFIG_FILE, "智能拾取設置", "拾取目標顏色")
            IniWrite(拾取搜索範圍, CONFIG_FILE, "智能拾取設置", "拾取搜索範圍")
            IniWrite(拾取間隔時間, CONFIG_FILE, "智能拾取設置", "拾取間隔時間")
            IniWrite(拾取最大距離, CONFIG_FILE, "智能拾取設置", "拾取最大距離")
            IniWrite(智能拾取開關 ? "true" : "false", CONFIG_FILE, "智能拾取設置", "智能拾取開關")
        } catch Error as err {
            ShowToolTip("❌ 保存設置到文件時發生錯誤: " . err.message, 3000, 1)
            return
        }
        
        ShowToolTip("✅ 設置已成功保存", 2000, 1)
        拾取設置GUI.Destroy()
    }
    
    測試拾取功能(*) {
        try {
            ; 隱藏當前GUI
            拾取設置GUI.Hide()
            
            ; 嘗試切換到遊戲視窗
            if (WinExist("Path of Exile")) {
                WinActivate("Path of Exile")
            } else if (WinExist("Path of Exile 2")) {
                WinActivate("Path of Exile 2")
            } else {
                ShowToolTip("❌ 找不到遊戲視窗 (Path of Exile 或 Path of Exile 2)", 3000, 1)
                拾取設置GUI.Show()
                return
            }
            
            Sleep(500)  ; 等待視窗切換
            
            ; 獲取當前視窗信息
            WinGetClientPos(&winX, &winY, &winWidth, &winHeight, "A")
            
            ; 計算搜索區域
            centerX := winX + winWidth // 2
            centerY := winY + winHeight // 2
            searchRadius := 拾取最大距離
            
            searchLeft := Max(winX, centerX - searchRadius)
            searchTop := Max(winY, centerY - searchRadius)
            searchRight := Min(winX + winWidth - 1, centerX + searchRadius)
            searchBottom := Min(winY + winHeight - 1, centerY + searchRadius)
            
            testInfo := "智能拾取測試 - 中心點模式`n`n"
            testInfo .= "當前設置:`n"
            testInfo .= "  • 目標顏色: " . 拾取目標顏色 . "`n"
            testInfo .= "  • 顏色容差: ±" . 拾取搜索範圍 . "`n"
            testInfo .= "  • 搜索半徑: " . 拾取最大距離 . " 像素`n`n"
            testInfo .= "搜索範圍:`n"
            testInfo .= "  • 中心點: (" . centerX . ", " . centerY . ")`n"
            testInfo .= "  • 搜索區域: (" . searchLeft . ", " . searchTop . ") 到 (" . searchRight . ", " . searchBottom . ")`n`n"
            testInfo .= "開始 3 秒測試..."
            
            ShowToolTip(testInfo, 8000, 1)
            
            if (!智能拾取開關) {
                開始智能拾取()
                SetTimer(測試完成重新顯示GUI, -3000)
            } else {
                ; 已運行中，測試3秒後重新顯示GUI
                SetTimer(測試完成重新顯示GUI, -3000)
            }
        } catch Error as e {
            ShowToolTip("測試失敗: " . e.message, 3000, 1)
            拾取設置GUI.Show()
        }
    }
    
    測試完成重新顯示GUI() {
        ; 測試完成後，如果智能拾取是在測試中啟動的，則停止它
        if (智能拾取開關) {
            停止智能拾取()
        }
        Sleep(500)
        拾取設置GUI.Show()
        ShowToolTip("✅ 測試完成，已重新開啟設置視窗", 2000, 1)
    }
    
    關閉拾取設置GUI(*) {
        拾取設置GUI.Destroy()
        Hotkey("Escape", "Off")
    }
}

; 偵測混傷穿透狀態
偵測混傷穿透() {
    try {
        if (!WinActive("Path of Exile") && !WinActive("Path of Exile 2")) {
            return
        }

        if (高級功能狀態 >= 2 && 顏色8_X != "error" && 顏色8_Y != "error") {
            混傷穿透顏色 := PixelGetColor(顏色8_X, 顏色8_Y)
            if (!顏色比對(混傷穿透顏色, 顏色8_C)) {
                if (偵測場景顏色 == "穩定") {
                    ; 🔧 二次確認
                    混傷穿透顏色_確認 := PixelGetColor(顏色8_X, 顏色8_Y)
                    if (!顏色比對(混傷穿透顏色_確認, 顏色8_C) && Toolbutton == 0) {
                        if (ToolTipOff == 0) {
                            ShowToolTip("⚡ 護盾被穿透，觸發緊急藥劑", 1000, 2)
                        }
                        ; 🔥 緊急藥劑邏輯 (可根據需求自訂)
                        if (藥劑按鍵1 != "error") {
                            智能喝水(藥劑按鍵1, "血條穿透偵測")
                        }
                    }
                }
            }
        }
    } catch {
        ; 錯誤處理
    }
}

; 偵測血條狀態 (增強版)
偵測血條狀態() {
    try {
        if (!WinActive("Path of Exile") && !WinActive("Path of Exile 2")) {
            return
        }
        
        if (高級功能狀態 >= 2 && 顏色1_X != "error" && 顏色1_Y != "error") {
            血條顏色 := PixelGetColor(顏色1_X, 顏色1_Y)
            
            ; 🔥 多點檢測血條狀況
            if (!顏色比對(血條顏色, 顏色1_C)) {  ; 血量異常
                if (偵測場景顏色 == "穩定") {
                    ; 🔧 檢查返角偵測點
                    if (顏色2_X != "error" && 顏色2_Y != "error") {
                        返角顏色 := PixelGetColor(顏色2_X, 顏色2_Y)
                        if (!顏色比對(返角顏色, 顏色2_C) && Toolbutton == 0) {
                            if (ToolTipOff == 0) {
                                ShowToolTip("🩸 血條異常，觸發治療", 1000, 2)
                            }
                            ; 🔥 智能治療邏輯
                            if (藥劑按鍵3 != "error") {
                                智能喝水(藥劑按鍵3, "血條偵測")
                            }
                        }
                    }
                }
            }
        }
    } catch {
        ; 錯誤處理
    }
}



; ======================================================================================================
; 血球魔力球偵測功能 (保持原有功能)
; ======================================================================================================

; 偵測魔力球
偵測魔力球() {
    try {
        global Toolbutton
        
        if (WinActive("Path of Exile") || WinActive("Path of Exile 2")) {  ; 鎖定POE視窗
            ; 🔍 檢查是否為文字輸入模式
            if (Toolbutton == 1) {
                return  ; 文字模式時停止偵測
            }
            
            if ((偵測魔球喝水打勾紀錄 == "+checked") && 高級功能狀態 >= 1) {  ; 🔥 與高級功能狀態整合
                if (顏色5_X == "error" || 顏色5_Y == "error" || 藥劑按鍵2 == "error") {
                    global 高級功能狀態 := 0
                    global Autodrinkbutton := 0
                    停止所有偵測()
                    ShowToolTip("❌ 魔球偵測設定錯誤，已關閉高級功能`n" .
                              "座標5X: " . 顏色5_X . ", 座標5Y: " . 顏色5_Y . "`n" . 
                              "藥劑按鍵2: " . 藥劑按鍵2, 4000, 1)
                    MsgBox("尚未設置偵測右下魔球座標或需要喝的藥劑，已自動關閉高級喝水功能。`n" .
                          "(Win + Z) 呼叫菜單 => 偵測喝水設置面板 => 設定藥劑與間隔，若無使用可關閉功能。`n" .
                          "設置偵測魔球座標 => 指定右下魔球低於滑鼠當前座標時喝水[Win + C]抓取代號 5。", "錯誤", 16)
                    return
                } else {
                    魔力池 := PixelGetColor(顏色5_X, 顏色5_Y)  ; 偵測喝水的
                    if (顏色比對(魔力池, 顏色5_C)) {  ; 如果顏色符合
                        ; 不做任何動作
                    } else {  ; 如果顏色不符合
                        if (偵測場景顏色 == "穩定") {
                            魔力池 := PixelGetColor(顏色5_X, 顏色5_Y)  ; 二次偵測
                            if (顏色比對(魔力池, 顏色5_C)) {  ; 如果顏色符合
                                ; 不做任何動作
                            } else {  ; 如果顏色不符合
                                if (Toolbutton == 0) {  ; 如果是在遊戲模式
                                    ; 🔥 使用智能喝水管理，防止重複喝水
                                    智能喝水(藥劑按鍵2, "魔力球偵測")
                                }
                            }
                        }
                    }
                }
            }
        }
    } catch {
        ; 錯誤處理
    }
}

; 偵測血球
偵測血球() {
    try {
        global Toolbutton
        
        if (WinActive("Path of Exile") || WinActive("Path of Exile 2")) {  ; 鎖定POE視窗
            ; 🔍 檢查是否為文字輸入模式
            if (Toolbutton == 1) {
                return  ; 文字模式時停止偵測
            }
            
            if (偵測血球池打勾紀錄 == "+checked" && 高級功能狀態 >= 1) {  ; 🔥 與高級功能狀態整合
                if (顏色4_X == "error" || 顏色4_Y == "error" || 藥劑按鍵4 == "error") {
                    global 高級功能狀態 := 0
                    global Autodrinkbutton := 0
                    停止所有偵測()
                    ShowToolTip("❌ 血球偵測設定錯誤，已關閉高級功能", 3000, 1)
                    MsgBox("尚未設置偵測血球池座標與需要喝的藥劑，已自動關閉高級喝水功能。`n" .
                          "高級喝水設置 => 偵測自動喝水 => 設定損血時需要的藥劑。`n" .
                          "設置偵測血球池座標 => [Win + C]抓取代號 4。", "錯誤", 16)
                    return
                } else {
                    血球池 := PixelGetColor(顏色4_X, 顏色4_Y)  ; 偵測喝水的
                    if (顏色比對(血球池, 顏色4_C)) {  ; 如果顏色符合
                        ; 不做任何動作
                    } else {  ; 如果顏色不符合
                        if (偵測場景顏色 == "穩定") {
                            血球池 := PixelGetColor(顏色4_X, 顏色4_Y)  ; 二次偵測
                            if (顏色比對(血球池, 顏色4_C)) {  ; 如果顏色符合
                                ; 不做任何動作
                            } else if (Toolbutton == 0) {  ; 如果顏色不符合，又是遊戲模式
                                ; 🔥 使用智能喝水管理，防止重複喝水
                                if (智能喝水(藥劑按鍵4, "血球池偵測")) {
                                    ; 喝水成功，無需額外動作
                                } else {
                                    ; 喝水被冷卻阻止，無需額外動作
                                }
                            }
                        }
                    }
                }
            }
        }
    } catch {
        ; 錯誤處理
    }
}

; 停止循環偵測

; 🔥 智能喝水管理函數 - 防止重複喝水
智能喝水(按鍵字串, 功能來源 := "通用") {
    try {
        if (按鍵字串 == "" || 按鍵字串 == "error") {
            return false
        }
        
        global 全域喝水冷卻, CONFIG_FILE
        當前時間 := A_TickCount
        
        ; 🔥 實時讀取最新的喝水間隔設置
        動態喝水間隔 := IniRead(CONFIG_FILE, "偵測喝水數據", "偵測喝水間隔", "1000")
        冷卻間隔 := Integer(動態喝水間隔)
        
        ; 🔥 檢查藥劑是否在保護間隔時間內，如果是則直接取消執行
        if (全域喝水冷卻.Has(按鍵字串)) {
            最後使用時間 := 全域喝水冷卻[按鍵字串]
            
            ; 如果還在冷卻期間，直接取消執行，返回false繼續下次偵測
            if (當前時間 - 最後使用時間 < 冷卻間隔) {
                剩餘時間 := 冷卻間隔 - (當前時間 - 最後使用時間)
                ; 降低提示頻率，避免過多訊息
                if (剩餘時間 > (冷卻間隔 * 0.8)) {  ; 只在冷卻前20%時提示一次
                    ShowToolTip("🔄 " . 按鍵字串 . " 鍵冷卻中 (" . 功能來源 . ") 剩餘:" . 剩餘時間 . "ms", 300, 3)
                }
                return false  ; 直接取消執行，繼續下次偵測
            }
        }
        
        ; 執行喝水動作
        發送按鍵序列(按鍵字串)
        
        ; 記錄使用時間
        全域喝水冷卻[按鍵字串] := 當前時間
        
        ; 顯示使用訊息
        ShowToolTip("🔴 使用 " . 按鍵字串 . " 鍵藥劑 (" . 功能來源 . ") 間隔:" . 冷卻間隔 . "ms", 800, 1)
        
        return true
    } catch {
        return false
    }
}

; 🔥 調試函數：顯示當前喝水冷卻狀態
顯示喝水冷卻狀態() {
    try {
        global 全域喝水冷卻, CONFIG_FILE
        當前時間 := A_TickCount
        
        冷卻間隔 := Integer(IniRead(CONFIG_FILE, "偵測喝水數據", "偵測喝水間隔", "1000"))
        
        狀態文字 := "🔍 喝水冷卻狀態:`n"
        
        if (全域喝水冷卻.Count > 0) {
            for 按鍵, 最後時間 in 全域喝水冷卻 {
                剩餘冷卻 := 冷卻間隔 - (當前時間 - 最後時間)
                if (剩餘冷卻 > 0) {
                    狀態文字 .= 按鍵 . " 鍵: 冷卻中 " . 剩餘冷卻 . "ms`n"
                } else {
                    狀態文字 .= 按鍵 . " 鍵: 可用`n"
                }
            }
        } else {
            狀態文字 .= "無冷卻記錄`n"
        }
        
        狀態文字 .= "設定間隔: " . 冷卻間隔 . "ms"
        
        ShowToolTip(狀態文字, 3000, 2)
    } catch {
        ShowToolTip("❌ 無法顯示冷卻狀態", 1000, 2)
    }
}

; 🔥 發送按鍵序列函數 (參考原始版本，支援多個按鍵如 135)
發送按鍵序列(按鍵字串) {
    try {
        if (按鍵字串 == "" || 按鍵字串 == "error") {
            return
        }
        
        ; 🔥 先處理特殊情況：如果是多位數字，逐個發送
        if (StrLen(按鍵字串) > 1 && RegExMatch(按鍵字串, "^[0-9]+$")) {
            ; 多位數字情況，如 "135"，逐個發送 1, 3, 5
            Loop Parse, 按鍵字串 {
                Send(A_LoopField)
                Sleep(50)  ; 短暫延遲確保按鍵註冊
            }
        } else {
            ; 單個按鍵或其他按鍵，直接發送
            Send(按鍵字串)
        }
    } catch {
        ; 發送失敗時的錯誤處理
    }
}

; 開始循環偵測 (保持向下兼容)
開始循環偵測() {
    try {
        ; 如果是舊版調用，自動轉為基礎模式
        if (Autodrinkbutton == 1 && 高級功能狀態 == 0) {
            global 高級功能狀態 := 1
        }
        
        if (高級功能狀態 >= 1) {  ; 開啟高級功能
            if (顏色1_X == "error" || 顏色1_Y == "error") {
                global 高級功能狀態 := 0
                global Autodrinkbutton := 0
                ShowToolTip("❌ 尚未設置場景偵測點，已關閉高級功能", 3000, 1)
                return
            }
            
            ; 🔥 使用新版統一計時器管理
            啟動基礎偵測()
        }
    } catch {
        ; 錯誤處理
    }
}

; 檢查場景是否穩定
檢查場景穩定狀態() {
    global 偵測場景顏色
    return (偵測場景顏色 = "穩定")
}

; 智能場景檢測 - 確保操作前場景穩定
智能場景檢測執行(operationName, operation) {
    global 偵測場景顏色, ToolTipOff
    
    ; 檢查是否在遊戲視窗
    if !檢查遊戲視窗() {
        return false
    }
    
    ; 檢查場景是否穩定
    if !檢查場景穩定狀態() {
        if (ToolTipOff = 0) {
            ShowToolTip("⚠️ 場景未穩定，暫緩執行: " . operationName, 2000, 4)
        }
        return false
    }
    
    ; 場景穩定，執行操作
    try {
        operation.Call()
        return true
    } catch as e {
        if (ToolTipOff = 0) {
            ShowToolTip("❌ 執行失敗: " . operationName . " - " . e.message, 3000, 4)
        }
        return false
    }
}

; 偵測場景變化 (升級版 - 基於250707邏輯優化)
偵測場景變化() {
    global
    
    try {
        ; 只在遊戲視窗且自動功能開啟時執行偵測
        if (!檢查遊戲視窗()) {
            return
        }
        
        ; 檢查是否有設定場景偵測座標
        if (!IsSet(顏色1_X) || !IsSet(顏色1_Y) || !IsSet(顏色1_C) || 
            顏色1_X = "error" || 顏色1_Y = "error" || 顏色1_C = "error") {
            return  ; 未設定場景偵測點時不執行
        }
        
        ; 獲取當前場景顏色
        currentColor := PixelGetColor(顏色1_X, 顏色1_Y)
        
        ; 檢查場景是否穩定（顏色匹配）
        if (顏色比對(currentColor, 顏色1_C)) {
            ; 場景顏色匹配 - 處理狀態轉換
            switch 偵測場景顏色 {
                case "變化中":
                    偵測場景顏色 := "中繼"
                    Sleep(1000)  ; 等待場景穩定
                    偵測場景顏色 := "穩定"
                    ; 場景穩定後恢復循環機制
                    恢復循環機制()
                    if (ToolTipOff = 0) {
                        ShowInfo("🔄 場景偵測：遊戲畫面已穩定", 2000)
                    }
                case "穩定":
                    ; 維持穩定狀態
                    偵測場景顏色 := "穩定"
            }
        } else {
            ; 場景顏色不匹配 - 場景正在變化
            if (偵測場景顏色 != "變化中") {
                暫停循環機制("場景變化")
                偵測場景顏色 := "變化中"
                
                ; 重置相關狀態
                Toolbutton := 0
                openI := 0
                當前倉庫頁 := 0
                
                if (ToolTipOff = 0) {
                    ShowToolTip("⚠️ 場景變化中，已暫停循環機制", 3000, 3)
                }
            }
            ; 🔥 移除持續的變化中提示，避免Loading期間干擾
        }
    } catch Error as e {
        ; 錯誤處理：重置為變化狀態以確保安全
        偵測場景顏色 := "變化中"
    }
}

; 暫停循環機制 (場景變化時)
暫停循環機制(reason := "") {
    global
    
    try {
        ; 藥劑系統已移除，不需要暫停
        
        ; 暫停高級功能的偵測計時器
        SetTimer(偵測血條喝水, 0)
        SetTimer(偵測魔力球, 0)
        SetTimer(偵測血條穿透, 0)
        SetTimer(偵測血球, 0)
        SetTimer(偵測血條返角, 0)
        SetTimer(偵測穿透返角, 0)
        
        ; 記錄暫停原因
        if (reason != "" && ToolTipOff = 0) {
            ShowToolTip("🛑 循環機制已暫停: " . reason, 2000, 4)
        }
    } catch {
        ; 忽略暫停過程中的錯誤
    }
}

; 恢復循環機制 (場景穩定後)
恢復循環機制() {
    global
    
    try {
        ; 恢復高級功能的偵測計時器（根據打勾狀態）
        if (高級功能狀態 >= 1) {
            ; 🔥 優先級1：返角功能（最高優先級，最小間隔）
            if (偵測血條返角打勾紀錄 == "+checked") {
                SetTimer(偵測血條返角, 10, 2147483647)  ; 10ms間隔，最高優先級
            }
            
            ; 🔥 優先級2：喝水相關功能
            if (偵測血條喝水打勾紀錄 == "+checked") {
                SetTimer(偵測血條喝水, 31, 1000)  ; 中等優先級
            }
            if ((偵測魔球喝水打勾紀錄 == "+checked")) {
                SetTimer(偵測魔力球, 51, 500)
            }
            if (偵測血球池打勾紀錄 == "+checked") {
                SetTimer(偵測血球, 41, 500)
            }
            
            ; 🔥 優先級3：穿透相關功能
            if (偵測血條穿透打勾紀錄 == "+checked") {
                SetTimer(偵測血條穿透, 37, 100)
            }
            if (偵測穿透返角打勾紀錄 == "+checked") {
                SetTimer(偵測穿透返角, 47, 1000)
            }
        } else {
            ; 🔥 即使高級功能關閉，返角功能仍需最高優先級獨立運作
            if (偵測血條返角打勾紀錄 == "+checked") {
                SetTimer(偵測血條返角, 10, 2147483647)  ; 10ms間隔，最高優先級
            }
        }
    } catch {
        ; 忽略恢復過程中的錯誤
    }
}

; ======================================================================================================
; F10 高級功能開關 (v2 穩定版 - 基於原始版本改良)
; ======================================================================================================

~F10:: {
    global 高級功能狀態, Autodrinkbutton
    
    ; 🔥 防抖動機制：防止快速連按導致狀態混亂
    static 上次F10時間 := 0
    當前時間 := A_TickCount
    if (當前時間 - 上次F10時間 < 500) {  ; 500ms內的重複按鍵忽略
        return
    }
    上次F10時間 := 當前時間
    
    try {
        ; 🔥 動態設置狀態檢查和引導 (檢查所有必須偵測點: 1,2,3)
        if (顏色1_X == "error" || 顏色1_Y == "error" || 
            顏色2_X == "error" || 顏色2_Y == "error" || 
            顏色3_X == "error" || 顏色3_Y == "error") {
            檢查設置狀態並顯示()
            return
        }
        
        ; 🔥 簡化的切換邏輯 (參考原始版本)
        if (高級功能狀態 == 0) {
            ; 關閉 → 基礎模式
            高級功能狀態 := 1
            Autodrinkbutton := 1
            ShowF10Status("🟢 基礎偵測模式 ON｜自動喝水功能啟動", 3000)
            啟動基礎偵測()
            
            ; 🔥 動態提示未設置的功能 (延遲到5秒後，避免與主狀態提示衝突)
            未設置提示 := Array()
            if (顏色6_X == "error") 未設置提示.Push("血條偵測")
            if (顏色5_X == "error") 未設置提示.Push("魔球偵測")
            if (顏色4_X == "error") 未設置提示.Push("血球池偵測")
            
            if (未設置提示.Length > 0) {
                提示文字 := "💡 建議設置: " . 未設置提示[1]
                if (未設置提示.Length > 1) {
                    提示文字 .= "等功能可提升智能喝水效果"
                } else {
                    提示文字 .= "功能可提升智能喝水效果"
                }
                SetTimer(() => ShowInfo(提示文字, 4000), -5000)  ; 改為5秒後顯示
            }
            
        } else if (高級功能狀態 == 1) {
            ; 基礎模式 → 完整模式  
            高級功能狀態 := 2
            ShowF10Status("🔵 完整偵測模式 ON｜全方位保護啟動", 3000)
            啟動完整偵測()
            
            ; 🔥 進階功能狀態提示 (延遲到5秒後，避免與主狀態提示衝突)
            進階功能狀態 := Array()
            if (顏色7_X != "error") 進階功能狀態.Push("穿透偵測已設置")
            if (顏色8_X != "error") 進階功能狀態.Push("穿透返角已設置")
            
            if (進階功能狀態.Length > 0) {
                SetTimer(() => ShowInfo("🎯 完整模式: " . 進階功能狀態[1]), -5000)  ; 改為5秒後顯示
            } else {
                SetTimer(() => ShowInfo("🎯 設置穿透偵測點可啟用進階功能"), -5000)  ; 改為5秒後顯示
            }
            
        } else {
            ; 完整模式 → 關閉
            高級功能狀態 := 0
            Autodrinkbutton := 0
            ShowF10Status("⭕ 偵測功能已關閉｜按F10重新啟動", 3000)
            停止所有偵測()
        }
        
        ; 🔧 保存狀態
        try {
            IniWrite(高級功能狀態, CONFIG_FILE, "高級功能狀態", "F10功能等級")
            狀態 := (Autodrinkbutton == 1) ? "開啟" : "關閉"
            IniWrite(狀態, CONFIG_FILE, "高級喝水狀態", "高級喝水狀態")
        } catch {
            ; 忽略保存錯誤
        }
        
        ; 🔥 簡短的狀態檢查提示 (已移除)
        
    } catch Error as err {
        ShowError("F10功能錯誤: " . err.message, 3000)
        ; 🛡️ 發生錯誤時安全關閉
        global 高級功能狀態 := 0
        global Autodrinkbutton := 0
        停止所有偵測()
    }
}

; ======================================================================================================
; 🔥 簡化的偵測管理函數 (避免循環調用)
; ======================================================================================================

; 啟動基礎偵測 (血球 + 魔力球 + 場景)
啟動基礎偵測() {
    try {
        ; 🔧 先停止避免衝突
        停止所有偵測()
        
        ; 🔥 重新讀取最新的設定
        更新全域偵測變數()
        
        ; 🔥 檢查場景偵測點
        if (顏色1_X == "error" || 顏色1_Y == "error") {
            global 高級功能狀態 := 0
            global Autodrinkbutton := 0
            ShowToolTip("❌ 請先設置場景偵測點", 3000, 1)
            return
        }
        
        ; 啟動基礎偵測計時器
        ; 收集啟動的偵測功能，統一顯示
        啟動列表 := []
        
        if (偵測血球池打勾紀錄 == "+checked" && 
            顏色4_X != "error" && 顏色4_Y != "error") {
            SetTimer(偵測血球, 41)
            啟動列表.Push("血球池")
        }
        if ((偵測魔球喝水打勾紀錄 == "+checked") && 
            顏色5_X != "error" && 顏色5_Y != "error") {
            SetTimer(偵測魔力球, 47)
            啟動列表.Push("魔力球")
        }
        SetTimer(偵測場景變化, 53, 10000)  ; 高優先級：用於判斷Loading狀態
        啟動列表.Push("場景變化")
        
        ; 啟動新增的基礎偵測功能
        if (偵測血條喝水打勾紀錄 == "+checked") {
            SetTimer(偵測血條喝水, 61)
            啟動列表.Push("血條喝水")
        }
        if (偵測血條返角打勾紀錄 == "+checked") {
            SetTimer(偵測血條返角, 10, 2147483647)  ; 最高優先級：10ms間隔
            啟動列表.Push("血條返角")
        }
        if (偵測穿透返角打勾紀錄 == "+checked") {
            SetTimer(偵測穿透返角, 71)
            啟動列表.Push("穿透返角")
        }
        
        ; 統一顯示所有啟動的偵測功能（僅在非F10調用時顯示，避免重複）
        ; 🔥 F10熱鍵會顯示自己的狀態，這裡不重複顯示
        ; if (啟動列表.Length > 0) {
        ;     偵測名稱 := ""
        ;     for 偵測 in 啟動列表 {
        ;         偵測名稱 .= 偵測 . "、"
        ;     }
        ;     偵測名稱 := RTrim(偵測名稱, "、")  ; 移除最後的頓號
        ;     ShowStatus("🟢 基礎偵測模式已啟動: " . 偵測名稱, 3000)
        ; }
        
    } catch Error as err {
        ShowError("基礎偵測啟動失敗: " . err.message, 3000)
    }
}

; 啟動完整偵測 (基礎 + 進階功能)
啟動完整偵測() {
    try {
        ; 先啟動基礎偵測
        ; 收集基礎偵測功能
        基礎啟動列表 := []
        
        ; 血球偵測
        if (偵測血球池打勾紀錄 == "+checked" && 
            顏色4_X != "error" && 顏色4_Y != "error") {
            SetTimer(偵測血球, 41)
            基礎啟動列表.Push("血球池")
        }
        if ((偵測魔球喝水打勾紀錄 == "+checked") && 
            顏色5_X != "error" && 顏色5_Y != "error") {
            SetTimer(偵測魔力球, 47)
            基礎啟動列表.Push("魔力球")
        }
        SetTimer(偵測場景變化, 53, 10000)  ; 高優先級：用於判斷Loading狀態
        基礎啟動列表.Push("場景變化")
        
        ; 啟動新增的基礎偵測功能
        if (偵測血條喝水打勾紀錄 == "+checked") {
            SetTimer(偵測血條喝水, 61)
            基礎啟動列表.Push("血條喝水")
        }
        if (偵測血條返角打勾紀錄 == "+checked") {
            SetTimer(偵測血條返角, 10, 2147483647)  ; 最高優先級：10ms間隔
            基礎啟動列表.Push("血條返角")
        }
        if (偵測穿透返角打勾紀錄 == "+checked") {
            SetTimer(偵測穿透返角, 71)
            基礎啟動列表.Push("穿透返角")
        }
        
        ; 🔥 確保全域變數是最新的
        更新全域偵測變數()
        
        ; 🔥 新增完整模式的高級偵測 - 只有在勾選相關選項時才啟動
        ; 🔥 收集完整模式啟動的額外偵測功能
        額外啟動列表 := []
        
        ; 混傷穿透偵測需要穿透相關選項勾選
        if ((偵測血條穿透打勾紀錄 == "+checked" || 偵測穿透返角打勾紀錄 == "+checked") && 
            顏色8_X != "error" && 顏色8_Y != "error") {
            SetTimer(偵測混傷穿透, 37)
            額外啟動列表.Push("混傷穿透")
        }
        
        ; 血條狀態偵測需要血條相關選項勾選
        if ((偵測血條喝水打勾紀錄 == "+checked" || 偵測血條返角打勾紀錄 == "+checked") && 
            顏色1_X != "error" && 顏色1_Y != "error") {
            SetTimer(偵測血條狀態, 43)
            額外啟動列表.Push("血條狀態")
        }
        
        ; 🔥 啟動進階偵測功能
        if (偵測血條穿透打勾紀錄 == "+checked") {
            SetTimer(偵測血條穿透, 71)
            額外啟動列表.Push("血條穿透")
        }
        if (偵測穿透返角打勾紀錄 == "+checked") {
            SetTimer(偵測穿透返角, 73)
            額外啟動列表.Push("穿透返角")
        }
        
        ; 🎯 統一顯示完整模式所有功能 (基礎+額外)
        全部功能列表 := []
        
        ; 合併基礎功能
        for 功能 in 基礎啟動列表 {
            全部功能列表.Push(功能)
        }
        
        ; 合併額外功能
        for 功能 in 額外啟動列表 {
            全部功能列表.Push(功能)
        }
        
        if (全部功能列表.Length > 0) {
            全部功能名稱 := ""
            for 功能 in 全部功能列表 {
                全部功能名稱 .= 功能 . "、"
            }
            全部功能名稱 := RTrim(全部功能名稱, "、")  ; 移除最後的頓號
            ; 🔥 F10熱鍵會顯示自己的狀態，這裡不重複顯示避免衝突
            ; ShowStatus("🔵 完整偵測模式已啟動: " . 全部功能名稱, 3000)
        }
    } catch {
        ShowError("完整偵測啟動失敗", 3000)
    }
}

; 停止所有偵測
停止所有偵測() {
    try {
        ; 🔧 停止所有計時器 (參考原始版本的停止邏輯)
        SetTimer(偵測血球, 0)
        SetTimer(偵測魔力球, 0)
        SetTimer(偵測場景變化, 0)
        SetTimer(偵測混傷穿透, 0)
        SetTimer(偵測血條狀態, 0)
        
        ; 停止新增的偵測功能
        SetTimer(偵測血條喝水, 0)
        SetTimer(偵測血條返角, 0)
        SetTimer(偵測血條穿透, 0)
        SetTimer(偵測穿透返角, 0)
        
        ; 藥劑系統已移除，不需要停止
        
    } catch {
        ; 忽略停止錯誤
    }
}

; ======================================================================================================
; 🔥 高級功能狀態監視與工具函數
; ======================================================================================================

; 獲取高級功能狀態文字
取得高級功能狀態文字() {
    global 高級功能狀態, 計時器狀態
    
    switch 高級功能狀態 {
        case 0:
            return "⭕ 偵測功能已關閉"
        case 1:
            活動計時器 := 0
            for 偵測名稱, 狀態 in 計時器狀態 {
                if (狀態) {
                    活動計時器++
                }
            }
            return "� 基礎偵測模式 (自動喝水ON，" . 活動計時器 . "個功能運行中)"
        case 2:
            活動計時器 := 0
            for 偵測名稱, 狀態 in 計時器狀態 {
                if (狀態) {
                    活動計時器++
                }
            }
            return "� 完整偵測模式 (全方位保護ON，" . 活動計時器 . "個功能運行中)"
        default:
            return "❓ 未知狀態"
    }
}

; 🔄 即時更新計時器狀態
更新即時計時器狀態() {
    global 計時器狀態
    
    try {
        ; 透過檢查SetTimer來確認計時器是否真的在運行
        ; 如果計時器正在運行，SetTimer返回週期值；如果停止，返回0
        計時器狀態["血球偵測"] := false
        計時器狀態["魔力球偵測"] := false  
        計時器狀態["場景偵測"] := false
        計時器狀態["ES偵測"] := false
        計時器狀態["血條偵測"] := false
        計時器狀態["血條喝水偵測"] := false
        計時器狀態["血條返角偵測"] := false
        計時器狀態["血條穿透偵測"] := false
        計時器狀態["穿透返角偵測"] := false
        
        ; 檢查每個計時器的實際運行狀態
        ; 這需要根據高級功能狀態來判斷
        if (高級功能狀態 >= 1) {
            ; 基礎模式的計時器
            if (偵測血球池打勾紀錄 == "+checked" && 
                顏色4_X != "error" && 顏色4_Y != "error") {
                計時器狀態["血球偵測"] := true
            }
            if ((偵測魔球喝水打勾紀錄 == "+Checked" || 偵測魔球喝水打勾紀錄 == "+checked") && 
                顏色5_X != "error" && 顏色5_Y != "error") {
                計時器狀態["魔力球偵測"] := true
            }
            計時器狀態["場景偵測"] := true
            
            if (偵測血條喝水打勾紀錄 == "+checked") {
                計時器狀態["血條喝水偵測"] := true
            }
            if (偵測血條返角打勾紀錄 == "+checked") {
                計時器狀態["血條返角偵測"] := true
            }
        }
        
        if (高級功能狀態 == 2) {
            ; 完整模式的額外計時器
            if ((偵測血條穿透打勾紀錄 == "+checked" || 偵測穿透返角打勾紀錄 == "+checked") && 
                顏色7_X != "error" && 顏色7_Y != "error") {
                計時器狀態["ES偵測"] := true
            }
            
            if ((偵測血條喝水打勾紀錄 == "+checked" || 偵測血條返角打勾紀錄 == "+checked") && 
                顏色1_X != "error" && 顏色1_Y != "error") {
                計時器狀態["血條偵測"] := true
            }
            
            if (偵測血條穿透打勾紀錄 == "+checked") {
                計時器狀態["血條穿透偵測"] := true
            }
            if (偵測穿透返角打勾紀錄 == "+checked") {
                計時器狀態["穿透返角偵測"] := true
            }
        }
        
    } catch {
        ; 更新失敗時保持原狀態
    }
}






        
        ; 🔥 功能詳情
        狀態報告 .= "🎯 F10 三段式模式切換說明:`n"
        狀態報告 .= "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━`n"
        狀態報告 .= "⭕ 關閉模式: 所有偵測功能停止，完全關閉狀態`n"
        狀態報告 .= "� 基礎偵測模式: 自動喝水ON (血球+魔力球+場景偵測)`n"
        狀態報告 .= "� 完整偵測模式: 全方位保護ON (基礎+血條+混傷穿透)`n`n"

        狀態報告 .= "�📊 當前計時器狀態:`n"
        for 偵測名稱, 狀態 in 計時器狀態 {
            狀態圖示 := 狀態 ? "🟢" : "🔴"
            間隔 := 偵測間隔設定.Has(偵測名稱) ? 偵測間隔設定[偵測名稱] . "ms" : "未設定"
            狀態報告 .= "• " . 偵測名稱 . ": " . 狀態圖示 . " (間隔: " . 間隔 . ")`n"
        }
        


; ======================================================================================================
; 系統控制熱鍵 (F11/F12)
; ======================================================================================================

; F11 重新載入腳本
~F11:: {
    try {
        Reload
    } catch Error as err {
        ShowToolTip("F11腳本重新載入錯誤: " . err.message, 3000)
    }
}

; F12 退出腳本
~F12:: {
    try {
        MsgBox("工具已結束 ლ(・ω・ლ)摸摸", "提示", 0)
        ExitApp
    } catch Error as err {
        ShowToolTip("F12腳本退出錯誤: " . err.message, 3000)
    }
}

; 🔥 Ctrl+F12 調試喝水冷卻狀態
^F12:: {
    try {
        顯示喝水冷卻狀態()
    } catch Error as err {
        ShowToolTip("調試錯誤: " . err.message, 2000)
    }
}

; ======================================================================================================
; 偵測喝水設置GUI相關函數
; ======================================================================================================

; 偵測喝水打勾紀錄轉換
偵測喝水打勾紀錄轉換() {
    global 偵測血條喝水打勾紀錄, 偵測血條返角打勾紀錄, 偵測魔球喝水打勾紀錄, 偵測血條穿透打勾紀錄, 偵測血條穿透返角打勾紀錄, 偵測血球池打勾紀錄
    global 藥劑按鍵1, 藥劑按鍵2, 藥劑按鍵3, 藥劑按鍵4, 偵測喝水間隔, 喝水提示開關, 使用者類型
    global 偵測血條喝水位置1, 偵測血條喝水位置2, 偵測魔球喝水位置, 偵測血條穿透位置7, 偵測血條穿透位置8, 偵測血球池位置
    
    try {
        ; 從INI檔案讀取設定
        偵測血條喝水打勾紀錄 := IniRead(CONFIG_FILE, "偵測喝水數據", "偵測血條喝水打勾紀錄", "-Checked")
        偵測血條返角打勾紀錄 := IniRead(CONFIG_FILE, "偵測喝水數據", "偵測血條返角打勾紀錄", "-Checked")
        偵測魔球喝水打勾紀錄 := IniRead(CONFIG_FILE, "偵測喝水數據", "偵測魔球喝水打勾紀錄", "-Checked")
        偵測血條穿透打勾紀錄 := IniRead(CONFIG_FILE, "偵測喝水數據", "偵測血條穿透打勾紀錄", "-Checked")
        偵測血條穿透返角打勾紀錄 := IniRead(CONFIG_FILE, "偵測喝水數據", "偵測血條穿透返角打勾紀錄", "-Checked")
        偵測血球池打勾紀錄 := IniRead(CONFIG_FILE, "偵測喝水數據", "偵測血球池打勾紀錄", "-Checked")
        
        ; 讀取偵測位置
        偵測血條喝水位置1 := IniRead(CONFIG_FILE, "偵測喝水數據", "偵測血條喝水位置1", "85")
        偵測血條喝水位置2 := IniRead(CONFIG_FILE, "偵測喝水數據", "偵測血條喝水位置2", "40")
        偵測魔球喝水位置 := IniRead(CONFIG_FILE, "偵測喝水數據", "偵測魔球喝水位置", "50")
        偵測血條穿透位置7 := IniRead(CONFIG_FILE, "偵測喝水數據", "偵測血條穿透位置7", "70")
        偵測血條穿透位置8 := IniRead(CONFIG_FILE, "偵測喝水數據", "偵測血條穿透位置8", "30")
        偵測血球池位置 := IniRead(CONFIG_FILE, "偵測喝水數據", "偵測血球池位置", "3")
        
        藥劑按鍵1 := IniRead(CONFIG_FILE, "偵測喝水數據", "藥劑按鍵1", "1")
        藥劑按鍵2 := IniRead(CONFIG_FILE, "偵測喝水數據", "藥劑按鍵2", "2")
        藥劑按鍵3 := IniRead(CONFIG_FILE, "偵測喝水數據", "藥劑按鍵3", "3")
        藥劑按鍵4 := IniRead(CONFIG_FILE, "偵測喝水數據", "藥劑按鍵4", "4")
        偵測喝水間隔 := IniRead(CONFIG_FILE, "偵測喝水數據", "偵測喝水間隔", "500")
        喝水提示開關 := IniRead(CONFIG_FILE, "偵測喝水數據", "喝水提示開關", "開啟")
        顏色容錯值 := IniRead(CONFIG_FILE, "偵測喝水數據", "顏色容錯值", "0")
        使用者類型 := IniRead(CONFIG_FILE, "授權數據", "使用者類型", "已贊助")
        
    } catch {
        ; 如果讀取失敗，使用預設值
        偵測血條喝水打勾紀錄 := "-Checked"
        偵測血條返角打勾紀錄 := "-Checked"
        偵測魔球喝水打勾紀錄 := "-Checked"
        偵測血條穿透打勾紀錄 := "-Checked"
        偵測血條穿透返角打勾紀錄 := "-Checked"
        偵測血球池打勾紀錄 := "-Checked"
        藥劑按鍵1 := "1"
        藥劑按鍵2 := "2"
        藥劑按鍵3 := "3"
        藥劑按鍵4 := "4"
        偵測喝水間隔 := "500"
        喝水提示開關 := "開啟"
        顏色容錯值 := 0
        使用者類型 := "已贊助"
    }
}

; 儲存狀態偵測設置
儲存狀態偵測設置() {
    try {
        global CONFIG_FILE, 狀態偵測GUI
        
        ; 🔥 獲取所有GUI控件的值
        try {
            values := 狀態偵測GUI.Submit(false)
        } catch {
            ShowToolTip("❌ 無法讀取GUI設定值", 3000, 1)
            return false
        }
        
        ; 🔥 儲存功能開關狀態
        IniWrite(values.HasProp("CheckBloodDrink") && values.CheckBloodDrink ? "+checked" : "", 
                CONFIG_FILE, "偵測喝水數據", "偵測血條喝水打勾紀錄")
        IniWrite(values.HasProp("CheckBloodReturn") && values.CheckBloodReturn ? "+checked" : "", 
                CONFIG_FILE, "偵測喝水數據", "偵測血條返角打勾紀錄")
        IniWrite(values.HasProp("CheckManaDrink") && values.CheckManaDrink ? "+checked" : "", 
                CONFIG_FILE, "偵測喝水數據", "偵測魔球喝水打勾紀錄")
        IniWrite(values.HasProp("CheckBloodPierce") && values.CheckBloodPierce ? "+checked" : "", 
                CONFIG_FILE, "偵測喝水數據", "偵測血條穿透打勾紀錄")
        IniWrite(values.HasProp("CheckPierceReturn") && values.CheckPierceReturn ? "+checked" : "", 
                CONFIG_FILE, "偵測喝水數據", "偵測穿透返角打勾紀錄")
        IniWrite(values.HasProp("CheckBloodPool") && values.CheckBloodPool ? "+checked" : "", 
                CONFIG_FILE, "偵測喝水數據", "偵測血球池打勾紀錄")
        
        ; 🔥 儲存藥劑按鍵設定
        if (values.HasProp("PotionKey1") && values.PotionKey1 != "") {
            IniWrite(values.PotionKey1, CONFIG_FILE, "偵測喝水數據", "藥劑按鍵1")
        }
        if (values.HasProp("PotionKey2") && values.PotionKey2 != "") {
            IniWrite(values.PotionKey2, CONFIG_FILE, "偵測喝水數據", "藥劑按鍵2")
        }
        if (values.HasProp("PotionKey3") && values.PotionKey3 != "") {
            IniWrite(values.PotionKey3, CONFIG_FILE, "偵測喝水數據", "藥劑按鍵3")
        }
        if (values.HasProp("PotionKey4") && values.PotionKey4 != "") {
            IniWrite(values.PotionKey4, CONFIG_FILE, "偵測喝水數據", "藥劑按鍵4")
        }
        
        ; 🔥 儲存偵測間隔設定
        if (values.HasProp("DetectInterval") && values.DetectInterval != "") {
            IniWrite(values.DetectInterval, CONFIG_FILE, "偵測喝水數據", "偵測喝水間隔")
            ; 🔥 同步更新全域變數
            global 偵測喝水間隔 := values.DetectInterval
        }
        
        ; 🔥 儲存工具提示設定
        if (values.HasProp("DrinkNotify")) {
            IniWrite(values.DrinkNotify == "關閉" ? "關閉" : "開啟", CONFIG_FILE, "偵測喝水數據", "工具提示開關")
        }
        
        ; 🎯 儲存顏色容錯值設定
        if (values.HasProp("ColorTolerance") && values.ColorTolerance != "") {
            容錯值 := Integer(values.ColorTolerance)
            IniWrite(容錯值, CONFIG_FILE, "偵測喝水數據", "顏色容錯值")
            global 顏色容錯值 := 容錯值  ; 即時更新全域變數
        }
        
        ; 🔥 儲存自訂偵測設定
        if (values.HasProp("EnableCustom") && values.EnableCustom) {
            IniWrite("true", CONFIG_FILE, "CustomDetection", "Enabled")
            if (values.HasProp("CustomX") && values.CustomX != "") {
                IniWrite(values.CustomX, CONFIG_FILE, "CustomDetection", "X")
            }
            if (values.HasProp("CustomY") && values.CustomY != "") {
                IniWrite(values.CustomY, CONFIG_FILE, "CustomDetection", "Y")
            }
            if (values.HasProp("TargetColor") && values.TargetColor != "") {
                IniWrite(values.TargetColor, CONFIG_FILE, "CustomDetection", "Color")
            }
            if (values.HasProp("TriggerKey") && values.TriggerKey != "") {
                IniWrite(values.TriggerKey, CONFIG_FILE, "CustomDetection", "Key")
            }
            if (values.HasProp("CustomInterval") && values.CustomInterval != "") {
                IniWrite(values.CustomInterval, CONFIG_FILE, "CustomDetection", "Interval")
            }
        } else {
            IniWrite("false", CONFIG_FILE, "CustomDetection", "Enabled")
        }
        
        ; 儲存成功後立即更新全域變數
        更新全域偵測變數()
        
        ShowToolTip("✅ 偵測喝水設定已成功保存！", 2500, 1)
        
        ; 儲存成功後自動關閉面板
        SetTimer(關閉狀態偵測GUI, -800)  ; 0.8秒後自動關閉，更快速的用戶體驗
        
        return true
        
    } catch Error as err {
        ShowToolTip("❌ 儲存設定失敗: " . err.message, 3000, 1)
        return false
    }
}

; 🔥 關閉狀態偵測GUI函數
關閉狀態偵測GUI() {
    try {
        global 狀態偵測GUI
        if (IsObject(狀態偵測GUI)) {
            狀態偵測GUI.Destroy()
        }
    } catch {
    }
}

; 載入偵測設定
載入偵測設定() {
    try {
        global CONFIG_FILE
        
        ; 🔥 從INI檔案讀取功能開關設定
        血條喝水 := IniRead(CONFIG_FILE, "偵測喝水數據", "偵測血條喝水打勾紀錄", "")
        血條返角 := IniRead(CONFIG_FILE, "偵測喝水數據", "偵測血條返角打勾紀錄", "")
        魔球喝水 := IniRead(CONFIG_FILE, "偵測喝水數據", "偵測魔球喝水打勾紀錄", "")
        血條穿透 := IniRead(CONFIG_FILE, "偵測喝水數據", "偵測血條穿透打勾紀錄", "")
        穿透返角 := IniRead(CONFIG_FILE, "偵測喝水數據", "偵測穿透返角打勾紀錄", "")
        血球池 := IniRead(CONFIG_FILE, "偵測喝水數據", "偵測血球池打勾紀錄", "")
        
        ; 🔥 讀取藥劑按鍵設定
        藥劑1 := IniRead(CONFIG_FILE, "偵測喝水數據", "藥劑按鍵1", "1")
        藥劑2 := IniRead(CONFIG_FILE, "偵測喝水數據", "藥劑按鍵2", "2")
        藥劑3 := IniRead(CONFIG_FILE, "偵測喝水數據", "藥劑按鍵3", "3")
        藥劑4 := IniRead(CONFIG_FILE, "偵測喝水數據", "藥劑按鍵4", "4")
        間隔 := IniRead(CONFIG_FILE, "偵測喝水數據", "偵測喝水間隔", "1000")
        提示 := IniRead(CONFIG_FILE, "偵測喝水數據", "工具提示開關", "開啟")
        
        ; 🔥 讀取自訂偵測設定
        自訂啟用 := IniRead(CONFIG_FILE, "CustomDetection", "Enabled", "false")
        自訂X := IniRead(CONFIG_FILE, "CustomDetection", "X", "")
        自訂Y := IniRead(CONFIG_FILE, "CustomDetection", "Y", "")
        自訂顏色 := IniRead(CONFIG_FILE, "CustomDetection", "Color", "0x000000")
        自訂按鍵 := IniRead(CONFIG_FILE, "CustomDetection", "Key", "Space")
        自訂間隔 := IniRead(CONFIG_FILE, "CustomDetection", "Interval", "1000")
        
        ; 🔥 應用設定到GUI控件 (使用正確的控件訪問方式)
        try {
            狀態偵測GUI["CheckBloodDrink"].Value := (血條喝水 == "+checked")
        } catch {
        }
        
        try {
            狀態偵測GUI["CheckBloodReturn"].Value := (血條返角 == "+checked")
        } catch {
        }
        
        try {
            狀態偵測GUI["CheckManaDrink"].Value := (魔球喝水 == "+checked")
        } catch {
        }
        
        try {
            狀態偵測GUI["CheckBloodPierce"].Value := (血條穿透 == "+checked")
        } catch {
        }
        
        try {
            狀態偵測GUI["CheckPierceReturn"].Value := (穿透返角 == "+checked")
        } catch {
        }
        
        try {
            狀態偵測GUI["CheckBloodPool"].Value := (血球池 == "+checked")
        } catch {
        }
        
        ; 🔥 載入藥劑按鍵設定
        try {
            狀態偵測GUI["PotionKey1"].Text := 藥劑1
        } catch {
        }
        try {
            狀態偵測GUI["PotionKey2"].Text := 藥劑2
        } catch {
        }
        try {
            狀態偵測GUI["PotionKey3"].Text := 藥劑3
        } catch {
        }
        try {
            狀態偵測GUI["PotionKey4"].Text := 藥劑4
        } catch {
        }
        try {
            狀態偵測GUI["DetectInterval"].Text := 間隔
        } catch {
        }
        
        ; 🔥 載入自訂偵測設定
        try {
            狀態偵測GUI["EnableCustom"].Value := (自訂啟用 == "true")
        } catch {
        }
        try {
            狀態偵測GUI["CustomX"].Text := 自訂X
        } catch {
        }
        try {
            狀態偵測GUI["CustomY"].Text := 自訂Y
        } catch {
        }
        try {
            狀態偵測GUI["TargetColor"].Text := 自訂顏色
        } catch {
        }
        try {
            狀態偵測GUI["TriggerKey"].Text := 自訂按鍵
        } catch {
        }
        try {
            狀態偵測GUI["CustomInterval"].Text := 自訂間隔
        } catch {
        }
        
        ShowToolTip("✅ 偵測喝水設定已載入完成！", 2000, 1)
        return true
        
    } catch {
        ShowToolTip("⚠️ 載入設定部分失敗", 3000, 1)
        return false
    }
}

; 🔥 更新全域偵測變數 (確保INI設定同步到全域變數)
更新全域偵測變數() {
    try {
        global CONFIG_FILE
        global 偵測血條喝水打勾紀錄, 偵測血條返角打勾紀錄, 偵測魔球喝水打勾紀錄
        global 偵測血條穿透打勾紀錄, 偵測穿透返角打勾紀錄, 偵測血球池打勾紀錄
        global 藥劑按鍵1, 藥劑按鍵2, 藥劑按鍵3, 藥劑按鍵4, 偵測喝水間隔, ToolTipOff
        
        ; 🔥 從INI檔案重新讀取所有設定並更新全域變數
        偵測血條喝水打勾紀錄 := IniRead(CONFIG_FILE, "偵測喝水數據", "偵測血條喝水打勾紀錄", "")
        偵測血條返角打勾紀錄 := IniRead(CONFIG_FILE, "偵測喝水數據", "偵測血條返角打勾紀錄", "")
        偵測魔球喝水打勾紀錄 := IniRead(CONFIG_FILE, "偵測喝水數據", "偵測魔球喝水打勾紀錄", "")
        偵測血條穿透打勾紀錄 := IniRead(CONFIG_FILE, "偵測喝水數據", "偵測血條穿透打勾紀錄", "")
        偵測穿透返角打勾紀錄 := IniRead(CONFIG_FILE, "偵測喝水數據", "偵測穿透返角打勾紀錄", "")  ; 🔧 修正變數名稱
        偵測血球池打勾紀錄 := IniRead(CONFIG_FILE, "偵測喝水數據", "偵測血球池打勾紀錄", "")
        
        ; 🔥 更新藥劑按鍵設定
        藥劑按鍵1 := IniRead(CONFIG_FILE, "偵測喝水數據", "藥劑按鍵1", "1")
        藥劑按鍵2 := IniRead(CONFIG_FILE, "偵測喝水數據", "藥劑按鍵2", "2")
        藥劑按鍵3 := IniRead(CONFIG_FILE, "偵測喝水數據", "藥劑按鍵3", "3")
        藥劑按鍵4 := IniRead(CONFIG_FILE, "偵測喝水數據", "藥劑按鍵4", "4")
        偵測喝水間隔 := IniRead(CONFIG_FILE, "偵測喝水數據", "偵測喝水間隔", "1000")
        
        ; 🔥 更新提示設定
        工具提示開關 := IniRead(CONFIG_FILE, "偵測喝水數據", "工具提示開關", "開啟")
        ToolTipOff := (工具提示開關 == "關閉")
        
        return true
    } catch Error as err {
        ShowToolTip("❌ 更新全域變數失敗: " . err.message, 3000, 1)
        return false
    }
}

; 更新狀態偵測GUI顯示狀態
更新狀態偵測GUI顯示() {
    try {
        global CONFIG_FILE, 狀態偵測GUI
        
        ; 讀取座標設定 (按新的邏輯順序)
        座標1X := IniRead(CONFIG_FILE, "顏色座標", "顏色1_X", "ERROR")  ; 場景偵測點
        座標1Y := IniRead(CONFIG_FILE, "顏色座標", "顏色1_Y", "ERROR")
        座標2X := IniRead(CONFIG_FILE, "顏色座標", "顏色2_X", "ERROR")  ; 對話框1
        座標2Y := IniRead(CONFIG_FILE, "顏色座標", "顏色2_Y", "ERROR")
        座標3X := IniRead(CONFIG_FILE, "顏色座標", "顏色3_X", "ERROR")  ; 對話框2
        座標3Y := IniRead(CONFIG_FILE, "顏色座標", "顏色3_Y", "ERROR")
        座標4X := IniRead(CONFIG_FILE, "顏色座標", "顏色4_X", "ERROR")  ; 血球池
        座標4Y := IniRead(CONFIG_FILE, "顏色座標", "顏色4_Y", "ERROR")
        座標5X := IniRead(CONFIG_FILE, "顏色座標", "顏色5_X", "ERROR")  ; 魔力球
        座標5Y := IniRead(CONFIG_FILE, "顏色座標", "顏色5_Y", "ERROR")
        座標6X := IniRead(CONFIG_FILE, "顏色座標", "顏色6_X", "ERROR")  ; 血條喝水
        座標6Y := IniRead(CONFIG_FILE, "顏色座標", "顏色6_Y", "ERROR")
        座標7X := IniRead(CONFIG_FILE, "顏色座標", "顏色7_X", "ERROR")  ; 血條返角
        座標7Y := IniRead(CONFIG_FILE, "顏色座標", "顏色7_Y", "ERROR")
        座標8X := IniRead(CONFIG_FILE, "顏色座標", "顏色8_X", "ERROR")  ; 血條穿透
        座標8Y := IniRead(CONFIG_FILE, "顏色座標", "顏色8_Y", "ERROR")
        座標9X := IniRead(CONFIG_FILE, "顏色座標", "顏色9_X", "ERROR")  ; 穿透返角
        座標9Y := IniRead(CONFIG_FILE, "顏色座標", "顏色9_Y", "ERROR")
        
        ; 讀取功能設定
        血條喝水 := IniRead(CONFIG_FILE, "偵測喝水數據", "偵測血條喝水打勾紀錄", "")
        血條返角 := IniRead(CONFIG_FILE, "偵測喝水數據", "偵測血條返角打勾紀錄", "")
        魔球喝水 := IniRead(CONFIG_FILE, "偵測喝水數據", "偵測魔球喝水打勾紀錄", "")
        血條穿透 := IniRead(CONFIG_FILE, "偵測喝水數據", "偵測血條穿透打勾紀錄", "")
        穿透返角 := IniRead(CONFIG_FILE, "偵測喝水數據", "偵測穿透返角打勾紀錄", "")
        血球池 := IniRead(CONFIG_FILE, "偵測喝水數據", "偵測血球池打勾紀錄", "")
        
        ; 讀取藥劑設定
        藥劑1 := IniRead(CONFIG_FILE, "偵測喝水數據", "藥劑按鍵1", "1")
        藥劑2 := IniRead(CONFIG_FILE, "偵測喝水數據", "藥劑按鍵2", "2")
        藥劑3 := IniRead(CONFIG_FILE, "偵測喝水數據", "藥劑按鍵3", "3")
        藥劑4 := IniRead(CONFIG_FILE, "偵測喝水數據", "藥劑按鍵4", "4")
        間隔 := IniRead(CONFIG_FILE, "偵測喝水數據", "偵測喝水間隔", "1000")
        提示 := IniRead(CONFIG_FILE, "偵測喝水數據", "工具提示開關", "開啟")
        容錯值 := IniRead(CONFIG_FILE, "偵測喝水數據", "顏色容錯值", "0")
        
        ; 設定GUI控件值 (使用正確的 +checked 格式檢查)
        if (IsObject(狀態偵測GUI)) {
            try {
                狀態偵測GUI["CheckBloodDrink"].Value := (血條喝水 == "+checked") ? 1 : 0
                狀態偵測GUI["CheckBloodReturn"].Value := (血條返角 == "+checked") ? 1 : 0  
                狀態偵測GUI["CheckManaDrink"].Value := (魔球喝水 == "+checked") ? 1 : 0
                狀態偵測GUI["CheckBloodPierce"].Value := (血條穿透 == "+checked") ? 1 : 0
                狀態偵測GUI["CheckPierceReturn"].Value := (穿透返角 == "+checked") ? 1 : 0
                狀態偵測GUI["CheckBloodPool"].Value := (血球池 == "+checked") ? 1 : 0
                
                狀態偵測GUI["PotionKey1"].Text := 藥劑1
                狀態偵測GUI["PotionKey2"].Text := 藥劑2
                狀態偵測GUI["PotionKey3"].Text := 藥劑3
                狀態偵測GUI["PotionKey4"].Text := 藥劑4
                
                ; 🔥 修正 DetectInterval ComboBox 的設定方式
                try {
                    ; 嘗試選擇匹配的選項
                    狀態偵測GUI["DetectInterval"].Choose(0)  ; 先清除選擇
                    狀態偵測GUI["DetectInterval"].Text := 間隔
                } catch {
                    ; 如果失敗，直接設定文字
                    狀態偵測GUI["DetectInterval"].Text := 間隔
                }
                
                ; 🔥 修正 DrinkNotify ComboBox 的設定方式 - 確保選項存在後再設定
                try {
                    if (提示 == "關閉") {
                        狀態偵測GUI["DrinkNotify"].Choose(2)  ; 選擇第2項 "關閉"
                    } else {
                        狀態偵測GUI["DrinkNotify"].Choose(1)  ; 選擇第1項 "開啟"
                    }
                } catch {
                    ; 如果ComboBox設定失敗，嘗試用Text屬性
                    狀態偵測GUI["DrinkNotify"].Text := 提示
                }
                
                ; 🎯 設定顏色容錯值下拉選單
                try {
                    ; 根據容錯值選擇對應的選項
                    switch 容錯值 {
                        case "0":  狀態偵測GUI["ColorTolerance"].Choose(1)
                        case "5":  狀態偵測GUI["ColorTolerance"].Choose(2)
                        case "10": 狀態偵測GUI["ColorTolerance"].Choose(3)
                        case "15": 狀態偵測GUI["ColorTolerance"].Choose(4)
                        case "20": 狀態偵測GUI["ColorTolerance"].Choose(5)
                        case "25": 狀態偵測GUI["ColorTolerance"].Choose(6)
                        default:   狀態偵測GUI["ColorTolerance"].Choose(1)  ; 預設選0 (精確比對)
                    }
                } catch {
                    ; 如果設定失敗，使用預設值
                    狀態偵測GUI["ColorTolerance"].Choose(1)
                }
                
                ; 更新座標顯示 (按新的邏輯順序)
                狀態偵測GUI["Coord1"].Text := (座標1X != "ERROR" && 座標1Y != "ERROR") ? 座標1X . ", " . 座標1Y : "未設定"  ; 場景偵測點
                狀態偵測GUI["Coord2"].Text := (座標2X != "ERROR" && 座標2Y != "ERROR") ? 座標2X . ", " . 座標2Y : "未設定"  ; 對話框1
                狀態偵測GUI["Coord3"].Text := (座標3X != "ERROR" && 座標3Y != "ERROR") ? 座標3X . ", " . 座標3Y : "未設定"  ; 對話框2
                狀態偵測GUI["Coord4"].Text := (座標4X != "ERROR" && 座標4Y != "ERROR") ? 座標4X . ", " . 座標4Y : "未設定"  ; 血球池
                狀態偵測GUI["Coord5"].Text := (座標5X != "ERROR" && 座標5Y != "ERROR") ? 座標5X . ", " . 座標5Y : "未設定"  ; 魔力球
                狀態偵測GUI["Coord6"].Text := (座標6X != "ERROR" && 座標6Y != "ERROR") ? 座標6X . ", " . 座標6Y : "未設定"  ; 血條喝水
                狀態偵測GUI["Coord7"].Text := (座標7X != "ERROR" && 座標7Y != "ERROR") ? 座標7X . ", " . 座標7Y : "未設定"  ; 血條返角
                狀態偵測GUI["Coord8"].Text := (座標8X != "ERROR" && 座標8Y != "ERROR") ? 座標8X . ", " . 座標8Y : "未設定"  ; 血條穿透
                狀態偵測GUI["Coord9"].Text := (座標9X != "ERROR" && 座標9Y != "ERROR") ? 座標9X . ", " . 座標9Y : "未設定"  ; 穿透返角
                
            } catch {
                ; 控件可能尚未創建，忽略錯誤
            }
        }

    } catch Error as err {
        ; 設定檔可能不存在，使用預設值
    }
}

; 開啟座標設定
開啟座標設定() {
    MsgBox("座標設定功能:`n`n1. 移動滑鼠到偵測點位置`n2. 按下 [Win + C] 抓取座標`n3. 根據提示輸入代號 1-9`n`n代號說明:`n1 = 場景偵測點 🎭`n2 = 對話框1 💬`n3 = 對話框2 💬`n4 = 血球池 🩸`n5 = 魔力球 🔵`n6 = 血條喝水 🩸`n7 = 血條返角 🔄`n8 = 血條穿透 ⚡`n9 = 穿透返角 🔄`n`n💡 背包座標請使用 F7 功能設定", "座標設定說明", 0x40)
}

; Win+C 座標偵測點記錄工具 - 現代版
#c:: {
    try {
        ; 獲取滑鼠當前位置和顏色
        MouseGetPos(&thisPosX, &thisPosY)
        colorabc := PixelGetColor(thisPosX, thisPosY)
        
        ; 創建Win+C座標抓取GUI
        CreateCoordinateGUI(thisPosX, thisPosY, colorabc)
        
    } catch Error as err {
        MsgBox("座標記錄時發生錯誤:`n" . err.message, "錯誤", 0x10)
    }
}

; 確認關閉狀態偵測GUI
確認關閉狀態偵測GUI(*) {
    global 狀態偵測GUI
    
    try {
        result := MsgBox("您尚未儲存設定，確定是否要直接關閉?", "提醒視窗", 0x4)
        if (result == "Yes") {
            ; 使用者確認關閉，關閉GUI
            try {
                if (IsObject(狀態偵測GUI)) {
                    狀態偵測GUI.Destroy()
                    狀態偵測GUI := ""
                }
            } catch {
                ; 關閉失敗，忽略
            }
        }
        ; 如果使用者選擇No，什麼都不做，GUI保持開啟
    } catch Error as err {
        ; 發生錯誤時直接關閉GUI
        try {
            if (IsObject(狀態偵測GUI)) {
                狀態偵測GUI.Destroy()
                狀態偵測GUI := ""
            }
        } catch {
            ; 關閉失敗，忽略
        }
    }
}

; ======================================================================================================
; 🔧 強制釋放按鍵 - 解決Ctrl鍵卡住問題
; ======================================================================================================
強制釋放按鍵(*) {
    try {
        釋放計數 := 0
        
        ; 檢查並釋放可能卡住的修飾鍵
        if (GetKeyState("Ctrl", "P")) {
            Send("{Ctrl up}")
            釋放計數++
            ShowToolTip("🔧 已釋放卡住的Ctrl鍵", 1500, 3)
        }
        
        if (GetKeyState("Shift", "P")) {
            Send("{Shift up}")
            釋放計數++
            ShowToolTip("🔧 已釋放卡住的Shift鍵", 1500, 4)
        }
        
        if (GetKeyState("Alt", "P")) {
            Send("{Alt up}")
            釋放計數++
            ShowToolTip("🔧 已釋放卡住的Alt鍵", 1500, 5)
        }
        
        ; 重置連點控制變數
        global clickStop := true
        global ctrlPressed := false
        
        ; 顯示總結信息
        if (釋放計數 > 0) {
            ShowToolTip("✅ 強制釋放完成，共釋放 " . 釋放計數 . " 個卡住的按鍵", 2500, 1)
        } else {
            ShowToolTip("✅ 檢查完成，所有按鍵狀態正常", 1500, 1)
        }
        
    } catch Error as e {
        ; 如果釋放按鍵失敗，記錄但不中斷程式
        ShowToolTip("⚠️ 按鍵釋放異常: " . e.Message, 2000, 1)
    }
}

; ======================================================================================================
; 🎮 F10 高級功能連動函數 (與偵測喝水設置GUI整合)
; ======================================================================================================

; 🔥 更新座標顯示狀態 - 從INI檔案讀取真實設置狀態
更新座標顯示狀態(gui對象) {
    try {
        global CONFIG_FILE, 顏色1_X, 顏色1_Y, 顏色2_X, 顏色2_Y, 顏色3_X, 顏色3_Y
        global 顏色4_X, 顏色4_Y, 顏色5_X, 顏色5_Y, 顏色6_X, 顏色6_Y, 顏色7_X, 顏色7_Y, 顏色8_X, 顏色8_Y, 顏色9_X, 顏色9_Y
        
        ; 🔧 座標映射表 (代號 => 變數名稱 => GUI控制項名稱)
        座標映射 := Map(
            1, {變數X: "顏色1_X", 變數Y: "顏色1_Y", 控制項: "Coord1", 名稱: "場景變化偵測"},
            2, {變數X: "顏色2_X", 變數Y: "顏色2_Y", 控制項: "Coord2", 名稱: "對話框1偵測"},
            3, {變數X: "顏色3_X", 變數Y: "顏色3_Y", 控制項: "Coord3", 名稱: "對話框2偵測"},
            4, {變數X: "顏色4_X", 變數Y: "顏色4_Y", 控制項: "Coord4", 名稱: "血球池偵測"},
            5, {變數X: "顏色5_X", 變數Y: "顏色5_Y", 控制項: "Coord5", 名稱: "魔力球偵測"},
            6, {變數X: "顏色6_X", 變數Y: "顏色6_Y", 控制項: "Coord6", 名稱: "血條喝水偵測"},
            7, {變數X: "顏色7_X", 變數Y: "顏色7_Y", 控制項: "Coord7", 名稱: "血條返角偵測"},
            8, {變數X: "顏色8_X", 變數Y: "顏色8_Y", 控制項: "Coord8", 名稱: "血條穿透偵測"},
            9, {變數X: "顏色9_X", 變數Y: "顏色9_Y", 控制項: "Coord9", 名稱: "穿透返角偵測"}
        )
        
        ; 🔥 遍歷所有座標並更新顯示狀態
        for 代號, 資料 in 座標映射 {
            try {
                ; 從全域變數取得座標值 (這些在啟動時已從INI載入)
                X值 := %資料.變數X%
                Y值 := %資料.變數Y%
                
                ; 判斷座標是否有效
                if (X值 == "error" || Y值 == "error" || X值 == "" || Y值 == "") {
                    顯示文字 := "❌ 未設定"
                    顏色代碼 := 0xFF0000  ; 紅色
                } else {
                    顯示文字 := "✅ (" . X值 . ", " . Y值 . ")"
                    顏色代碼 := 0x008000  ; 綠色
                }
                
                ; 更新GUI顯示
                gui對象[資料.控制項].Text := 顯示文字
                gui對象[資料.控制項].SetFont("c" . Format("0x{:06X}", 顏色代碼))
                
            } catch Error as err {
                ; 如果取得變數失敗，顯示錯誤狀態
                gui對象[資料.控制項].Text := "⚠️ 讀取失敗"
                gui對象[資料.控制項].SetFont("cRed")
            }
        }
        
        ; 🔥 統計設置完成度
        已設置數量 := 0
        總數量 := 座標映射.Count
        
        for 代號, 資料 in 座標映射 {
            X值 := %資料.變數X%
            Y值 := %資料.變數Y%
            if (X值 != "error" && Y值 != "error" && X值 != "" && Y值 != "") {
                已設置數量++
            }
        }
        
        完成度百分比 := Round((已設置數量 / 總數量) * 100)
        
        ; 顯示更新完成訊息
        ShowToolTip("🔄 座標狀態已更新 | 設置完成度: " . 已設置數量 . "/" . 總數量 . " (" . 完成度百分比 . "%)", 2000, 1)
        
    } catch Error as err {
        ShowToolTip("⚠️ 座標狀態更新失敗: " . err.message, 3000, 1)
    }
}

; 查看F10狀態 - 使用專門的GUI顯示詳細狀態
查看F10狀態() {
    try {
        global 高級功能狀態, 計時器狀態, 偵測間隔設定
        
        狀態報告 := "🎮 F10 高級功能完整狀態監控`n"
        狀態報告 .= "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━`n"
        狀態報告 .= "🔧 目前狀態: " . 取得高級功能狀態文字() . "`n`n"
        
        ; 🔥 設置狀態檢查
        狀態報告 .= "📋 必要設置檢查:`n"
        場景設置狀態 := (顏色1_X != "error" && 顏色1_Y != "error") ? "✅ 已設置" : "❌ 未設置"
        血球設置狀態 := (顏色4_X != "error" && 顏色4_Y != "error") ? "✅ 已設置" : "❌ 未設置"
        魔球設置狀態 := (顏色5_X != "error" && 顏色5_Y != "error") ? "✅ 已設置" : "❌ 未設置"
        混傷穿透狀態 := (顏色8_X != "error" && 顏色8_Y != "error") ? "✅ 已設置" : "❌ 未設置"
        
        狀態報告 .= "• 場景偵測點 (必須): " . 場景設置狀態 . " - [Win+C] 代號1`n"
        狀態報告 .= "• 血球偵測點: " . 血球設置狀態 . " - [Win+C] 代號4`n"
        狀態報告 .= "• 魔球偵測點: " . 魔球設置狀態 . " - [Win+C] 代號5`n"
        狀態報告 .= "• 混傷穿透偵測點: " . 混傷穿透狀態 . " - [Win+C] 代號8`n`n"
        
        狀態報告 .= "📊 即時計時器運行狀態:`n"
        狀態報告 .= "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━`n"
        
        運行中計時器 := 0
        for 偵測名稱, 狀態 in 計時器狀態 {
            狀態圖示 := 狀態 ? "🟢 運行中" : "🔴 已停止"
            間隔 := 偵測間隔設定.Has(偵測名稱) ? 偵測間隔設定[偵測名稱] . "ms" : "未設定"
            狀態報告 .= "• " . 偵測名稱 . ": " . 狀態圖示 . " (間隔: " . 間隔 . ")`n"
            if (狀態) {
                運行中計時器++
            }
        }
        
        狀態報告 .= "`n📈 運行統計: " . 運行中計時器 . "/" . 計時器狀態.Count . " 個計時器正在運行`n`n"
        
        狀態報告 .= "`n🎮 操作說明:`n"
        狀態報告 .= "• F10: 循環切換模式 (關閉→基礎→完整→關閉)`n"
        狀態報告 .= "• 基礎模式: 血球+魔力球+場景偵測`n"
        狀態報告 .= "• 完整模式: 基礎+血條+混傷穿透`n`n"

        if (場景設置狀態 == "❌ 未設置") {
            狀態報告 .= "🚨 請先完成場景偵測點設置才能正常使用 F10 功能！`n"
            狀態報告 .= "設置方法: [Win+Z] → 偵測喝水設置 → 場景偵測點設置"
        }
        
        ; 🔥 創建專門的狀態GUI，使用更大字體
        狀態GUI := Gui("+Resize", "F10 高級功能狀態監控台")
        狀態GUI.BackColor := "0xF0F8FF"
        狀態GUI.SetFont("s11", "Microsoft JhengHei")  ; 增大字體
        
        狀態GUI.Add("Edit", "x10 y10 w680 h400 ReadOnly VScroll", 狀態報告)
        狀態GUI.Add("Button", "x300 y420 w100 h30", "確定").OnEvent("Click", (*) => 狀態GUI.Destroy())
        
        ; 🔥 支援ESC關閉
        狀態GUI.OnEvent("Escape", (*) => 狀態GUI.Destroy())
        
        狀態GUI.Show("w700 h460")
        ShowToolTip("📊 正在顯示 F10 詳細狀態...", 1500, 1)
        
    } catch Error as err {
        ShowToolTip("狀態查看失敗: " . err.message, 3000, 1)
    }
}

; F10完整教學
F10完整教學() {
    try {
        ; 🔥 使用更大的字體和更清晰的格式
        教學內容 .= "🎓 F10 高級功能完整使用教學`n"
        教學內容 .= "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━`n`n"
        
        教學內容 .= "📋 使用前準備:`n"
        教學內容 .= "1️ 必須設置: 場景偵測點 (代號1) - 用於判斷遊戲狀態`n"
        教學內容 .= "2️ 必須設置: 對話框1偵測 (代號2) - Enter對話框偵測`n"
        教學內容 .= "3️ 必須設置: 對話框2偵測 (代號3) - 位移對話框偵測`n"
        教學內容 .= "4️ 建議設置: 血球偵測點 (代號4) - 血量不足時自動喝水`n"
        教學內容 .= "5️ 建議設置: 魔球偵測點 (代號5) - 魔力不足時自動喝水`n"
        教學內容 .= "6️ 進階設置: 混傷穿透偵測點 (代號8) - 完整模式使用`n`n"
        
        教學內容 .= "🎮 F10 操作方式:`n"
        教學內容 .= "🔴 F10 按下: 🔴關閉狀態 → 🟡基礎模式`n"
        教學內容 .= "   └ 啟動: 血球偵測 + 魔球偵測 + 場景偵測`n"
        教學內容 .= "🟡 F10 按下: 🟡基礎狀態 → 🟢完整模式`n"
        教學內容 .= "   └ 包含: 基礎功能 + 混傷穿透 + 血條狀態 + 穿透偵測`n"
        教學內容 .= "🟢 F10 按下: 🟢完整狀態 → 🔴關閉模式`n"
        教學內容 .= "   └ 停止所有偵測功能，節省系統資源`n`n"
        
        教學內容 .= "⚙️ 進階功能:`n"
        教學內容 .= "• 狀態自動保存: 關閉腳本後重開會恢復上次狀態`n"
        教學內容 .= "• 智能檢查: 自動檢測設置完成度，提醒未完成項目`n"
        教學內容 .= "• 質數間隔: 使用37,41,43,47,53,59ms避免計時器衝突`n`n"
        
        教學內容 .= "💡 使用建議:`n"
        教學內容 .= "• 新手建議: 先完成基本設置，使用基礎模式測試無誤後再升級`n"
        教學內容 .= "• 日常使用: 基礎模式已足夠大部分情況，完整模式適合高難度內容`n"
        教學內容 .= "• 最佳體驗: 搭配 [Win+Z] 主選單的其他功能一起使用`n"
        教學內容 .= "• 循環切換: F10 會根據當前狀態自動切換到下一個模式`n`n"
        
        教學內容 .= "🚨 注意事項:`n"
        教學內容 .= "• 僅在 Path of Exile / Path of Exile 2 遊戲視窗中生效`n"
        教學內容 .= "• 場景偵測點是核心功能，其他偵測點可依需求設置`n"
        教學內容 .= "• 建議定期使用 [Win+C] 重新校正偵測座標"
        
        ; 🔥 創建專門的教學視窗，使用更大字體
        教學GUI := Gui("+Resize", "F10 高級功能完整教學")
        教學GUI.BackColor := "0xF0F8FF"
        教學GUI.SetFont("s11", "Microsoft JhengHei")  ; 增大字體
        
        教學GUI.Add("Edit", "x10 y10 w780 h500 ReadOnly VScroll", 教學內容)
        教學GUI.Add("Button", "x350 y520 w100 h30", "確定").OnEvent("Click", (*) => 教學GUI.Destroy())
        
        ; 🔥 支援ESC關閉
        教學GUI.OnEvent("Escape", (*) => 教學GUI.Destroy())
        
        教學GUI.Show("w800 h560")
        
    } catch Error as err {
        ShowToolTip("教學顯示失敗: " . err.message, 3000, 1)
    }
}

; � F3設定指導 - 快速顯示GUI
顯示F3設定指導() {
    try {
        ; 創建圖片式指導GUI
        global F3指導GUI := Gui("+AlwaysOnTop -MaximizeBox", "🎒 F3清包設定")
        F3指導GUI.BackColor := "0xF0F8FF"
        F3指導GUI.MarginX := 15
        F3指導GUI.MarginY := 10
        
        ; 標題
        F3指導GUI.SetFont("s14 Bold", "Microsoft JhengHei")
        F3指導GUI.Add("Text", "x15 y10 w470 Center cNavy", "🎒 F3清包功能")
        
        ; 檢查並顯示圖片
        圖片路徑 := ""
        if FileExist(A_ScriptDir . "\image\F3圖例.png")
            圖片路徑 := A_ScriptDir . "\image\F3圖例.png"
        else if FileExist(A_ScriptDir . "\F3圖例.png")
            圖片路徑 := A_ScriptDir . "\F3圖例.png"
            
        if (圖片路徑 != "") {
            ; 顯示圖片
            F3指導GUI.Add("Picture", "x15 y40 w470 h280", 圖片路徑)
        } else {
            ; 如果沒有圖片，顯示簡化說明
            F3指導GUI.SetFont("s11", "Microsoft JhengHei")
            F3指導GUI.Add("Text", "x15 y40 w470 cRed Center", "⚠️ 請先設定背包位置")
            F3指導GUI.Add("Text", "x15 y70 w470 Center", "按 I 開啟背包 → 按 F7 設定位置")
            F3指導GUI.Add("Text", "x15 y100 w470 Center", "設定完成後按 F3 即可清包")
        }
        
        ; 操作按鈕
        F3指導GUI.SetFont("s11 Bold", "Microsoft JhengHei")
        F3指導GUI.Add("Button", "x15 y340 w150 h35", "📋 開啟F7設定").OnEvent("Click", 開啟F7設定)
        F3指導GUI.Add("Button", "x175 y340 w150 h35", "❌ 關閉").OnEvent("Click", (*) => F3指導GUI.Destroy())
        
        ; 顯示GUI
        F3指導GUI.Show("w500 h390")
        
        ; ESC快速關閉
        F3指導GUI.OnEvent("Escape", (*) => F3指導GUI.Destroy())
        
        ; 按鈕事件函數
        開啟F7設定(*) {
            F3指導GUI.Destroy()
            F7_座標設置()
        }
        
    } catch Error as err {
        MsgBox("顯示F3指導時發生錯誤: " . err.message, "錯誤", 0x10)
    }
}

; �🎯 座標抓取教學
; 💬 對話框設定指導 - 友善GUI
顯示對話框設定指導() {
    try {
        ; 檢查是否已有對話框指導GUI開啟，如果有則先關閉
        try {
            對話框指導GUI.Destroy()
        } catch {
            ; 忽略錯誤，GUI可能不存在
        }
        
        ; 創建友善的對話框設定指導GUI
        global 對話框指導GUI := Gui("-MaximizeBox", "💬 Enter對話框偵測設定")
        對話框指導GUI.BackColor := "0xF0F8FF"
        對話框指導GUI.MarginX := 20
        對話框指導GUI.MarginY := 15
        
        ; 標題區域
        對話框指導GUI.SetFont("s16 Bold", "Microsoft JhengHei")
        對話框指導GUI.Add("Text", "x20 y15 w560 Center cNavy", "💬 Enter對話框智能偵測設定")
        對話框指導GUI.Add("Text", "x20 y50 w560 h3 Background0x4169E1")
        
        ; 重要性說明
        對話框指導GUI.SetFont("s12 Bold", "Microsoft JhengHei")
        對話框指導GUI.Add("Text", "x20 y70 w560 cRed", "⚠️ 重要功能說明")
        
        對話框指導GUI.SetFont("s11", "Microsoft JhengHei")
        對話框指導GUI.Add("Text", "x20 y100 w560", "這個功能可以防止在聊天輸入時誤觸遊戲快捷鍵，是非常重要的保護機制。")
        對話框指導GUI.Add("Text", "x20 y125 w560", "當系統偵測到對話框開啟時，會自動暫停所有快捷鍵功能，確保輸入安全。")
        
        ; 設定步驟
        對話框指導GUI.SetFont("s12 Bold cBlue", "Microsoft JhengHei")
        對話框指導GUI.Add("Text", "x20 y160 w560", "📋 設定步驟：")
        
        對話框指導GUI.SetFont("s11", "Microsoft JhengHei")
        對話框指導GUI.Add("Text", "x20 y185 w560", "1️ 進入遊戲，按 Enter 鍵開啟聊天框")
        對話框指導GUI.Add("Text", "x20 y210 w560", "2️ 將滑鼠指向聊天框的黑色區域")
        對話框指導GUI.Add("Text", "x20 y235 w560", "3️ 按下 [Win+C] 鍵抓取座標，輸入代號 2")
        對話框指導GUI.Add("Text", "x20 y260 w560", "4️ 再次移動滑鼠到另一個黑色區域位置")
        對話框指導GUI.Add("Text", "x20 y285 w560", "5️ 按下 [Win+C] 鍵抓取座標，輸入代號 3")
        
        ; 技術提示
        對話框指導GUI.SetFont("s12 Bold cGreen", "Microsoft JhengHei")
        對話框指導GUI.Add("Text", "x20 y320 w560", "💡 技術提示：")
        
        對話框指導GUI.SetFont("s11", "Microsoft JhengHei")
        對話框指導GUI.Add("Text", "x20 y345 w560", "🔸 選擇純黑色區域效果最佳")
        對話框指導GUI.Add("Text", "x20 y365 w560", "🔸 兩個偵測點建議設在不同位置，提高準確性")
        對話框指導GUI.Add("Text", "x20 y385 w560", "🔸 設定完成後會自動啟用智能保護")
        
        ; 操作按鈕區域
        對話框指導GUI.SetFont("s11 Bold", "Microsoft JhengHei")
        對話框指導GUI.Add("Button", "x20 y425 w150 h35", "📋 開啟Win+C設定").OnEvent("Click", 開啟WinC設定)
        對話框指導GUI.Add("Button", "x180 y425 w150 h35", "🖼️ 查看教學圖片").OnEvent("Click", 查看教學圖片)
        對話框指導GUI.Add("Button", "x340 y425 w120 h35", "⏭️ 稍後設定").OnEvent("Click", 稍後設定選項)
        對話框指導GUI.Add("Button", "x470 y425 w110 h35", "❌ 關閉").OnEvent("Click", (*) => 對話框指導GUI.Destroy())
        
        ; 顯示GUI
        對話框指導GUI.Show("w600 h480")
        
        ; ESC快速關閉
        對話框指導GUI.OnEvent("Escape", (*) => 對話框指導GUI.Destroy())
        
        ; 按鈕事件函數
        開啟WinC設定(*) {
            對話框指導GUI.Destroy()
            座標定位功能()
        }
        
        查看教學圖片(*) {
            try {
                ; 使用本地圖片而非網頁圖片
                顯示對話框設定圖片()
            } catch {
                ShowToolTip("❌ 無法開啟教學圖片", 3000, 1)
            }
        }
        
        稍後設定選項(*) {
            global Enter除錯提醒次數, CONFIG_FILE
            
            ; 🔄 重置提醒次數，讓使用者之後還能看到指導
            Enter除錯提醒次數 := 0
            IniWrite(Enter除錯提醒次數, CONFIG_FILE, "系統設定", "Enter除錯提醒次數")
            
            ; 友善提醒
            ShowToolTip("💡 已設定為稍後配置`n" .
                       "🎯 下次按 Enter 鍵時會重新顯示設定指導`n" .
                       "🔧 您也可以隨時按 Win+C 進行手動設定", 5000, 1)
            
            對話框指導GUI.Destroy()
        }
        
    } catch Error as err {
        MsgBox("顯示對話框指導時發生錯誤: " . err.message, "錯誤", 0x10)
    }
}

; 🎯 背包顏色定位指導
顯示背包顏色定位指導() {
    try {
        ; 創建友善的背包顏色定位指導GUI
        global 背包顏色指導GUI := Gui("+AlwaysOnTop -MaximizeBox", "🎒 背包顏色定位設定指導")
        背包顏色指導GUI.BackColor := "0x2D2D2D"
        背包顏色指導GUI.MarginX := 25
        背包顏色指導GUI.MarginY := 20
        
        ; 設定標題字體並添加標題
        背包顏色指導GUI.SetFont("s14 Bold", "Microsoft YaHei UI")
        背包顏色指導GUI.Add("Text", "x25 y20 w450 Center cWhite", "🎒 背包顏色定位設定指導")
        
        ; 設定說明文字字體並添加說明
        背包顏色指導GUI.SetFont("s10 Normal", "Microsoft YaHei UI")
        說明文字 := "✅ 您已成功設定背包座標（F7）`n"
        說明文字 .= "⚠️  但尚未進行背包顏色定位`n`n"
        說明文字 .= "🔍 為什麼需要背包顏色定位？`n"
        說明文字 .= "• F3 掃描式清包需要識別空格的顏色`n"
        說明文字 .= "• 避免重複點擊已有物品的格子`n"
        說明文字 .= "• 提高清包效率和準確性`n`n"
        說明文字 .= "📋 操作步驟：`n"
        說明文字 .= "1. 打開背包，確保背包是空的（60格都無物品）`n"
        說明文字 .= "2. 按 Win+F3 打開F3選單`n"
        說明文字 .= "3. 點擊「🎯 背包顏色定位」按鈕`n"
        說明文字 .= "4. 系統會自動掃描並儲存空格顏色`n"
        說明文字 .= "5. 完成後即可使用 F3 清包功能"
        
        背包顏色指導GUI.Add("Text", "x25 y60 w450 h320 cWhite", 說明文字)
        
        ; 設定按鈕字體
        背包顏色指導GUI.SetFont("s11 Bold", "Microsoft YaHei UI")
        
        ; 按鈕群組 - 調整位置避免覆蓋文字
        立即設定按鈕 := 背包顏色指導GUI.Add("Button", "x25 y400 w140 h40", "🎯 立即設定")
        立即設定按鈕.OnEvent("Click", 立即開始背包顏色定位)
        
        F3選單按鈕 := 背包顏色指導GUI.Add("Button", "x175 y400 w140 h40", "📋 打開F3選單")
        F3選單按鈕.OnEvent("Click", 打開F3選單)
        
        稍後按鈕 := 背包顏色指導GUI.Add("Button", "x325 y400 w140 h40", "⏰ 稍後設定")
        稍後按鈕.OnEvent("Click", 稍後設定背包顏色)
        
        ; 顯示GUI - 增加高度
        背包顏色指導GUI.Show("w500 h470")
        
        ; 按鈕事件處理函數
        立即開始背包顏色定位(*) {
            ShowToolTip("🎯 請確保背包已打開且為空（60格都無物品）", 3000, 1)
            背包顏色指導GUI.Destroy()
            
            ; 等待1秒讓使用者準備
            Sleep(1000)
            
            ; 執行背包顏色定位
            快速掃描背包顏色並儲存()
        }
        
        打開F3選單(*) {
            背包顏色指導GUI.Destroy()
            ; 打開F3選單
            F3_選單()
        }
        
        稍後設定背包顏色(*) {
            ShowToolTip("💡 稍後請按 Win+F3 打開選單進行背包顏色定位`n" .
                       "🎯 選擇「🎯 背包顏色定位」即可設定", 4000, 1)
            背包顏色指導GUI.Destroy()
        }
        
    } catch Error as err {
        MsgBox("顯示背包顏色定位指導時發生錯誤: " . err.message, "錯誤", 0x10)
    }
}

; 🎯 座標抓取教學
座標抓取教學() {
    try {
        教學內容 := "🎯 智能偵測系統 - 座標抓取教學`n"
        教學內容 .= "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━`n`n"
        
        教學內容 .= "🧠 偵測原理:`n"
        教學內容 .= "系統會在您指定的座標位置偵測顏色變化來判斷血量/魔量狀態`n"
        教學內容 .= "• 座標越接近滿血位置 = 提早觸發功能 (血量約80-90%時就喝水)`n"
        教學內容 .= "• 座標越接近空血位置 = 延後觸發功能 (血量約30-50%時才喝水)`n`n"
        
        教學內容 .= "🎯 操作步驟:`n"
        教學內容 .= "1. 將滑鼠移到要偵測的位置`n"
        教學內容 .= "2. 按下 [Win+C] 抓取座標`n"
        教學內容 .= "3. 輸入對應代號 (1-9)`n"
        教學內容 .= "4. 🎯 系統會顯示準心標示目前抓取的座標位置`n"
        教學內容 .= "5. 如座標位置不正確，請按 [ESC] 關閉面板，重新定位滑鼠再抓取`n`n"
        
        教學內容 .= "📍 偵測點設置指南 (依優先順序排列):`n"
        教學內容 .= "代號1: 🎮 場景變化偵測 - 遊戲狀態判斷 ⭐必須設置`n"
        教學內容 .= "       (指向遊戲UI固定位置，判斷是否在遊戲中)`n`n"
        
        教學內容 .= "代號2: 💬 對話框1偵測 - Enter對話框偵測 ⭐必須設置`n"
        教學內容 .= "       (指向NPC對話框位置，防止誤觸)`n`n"
        
        教學內容 .= "代號3: � 對話框2偵測 - 位移對話框偵測 ⭐必須設置`n"
        教學內容 .= "       (指向物品位移對話框，防止誤觸)`n`n"
        
        教學內容 .= "代號4: 🟥 血球池偵測 - 抓取血球「有血」時的顏色 ⭐`n"
        教學內容 .= "       (左下角紅色血球，紅色消失時自動喝血水)`n`n"
        
        教學內容 .= "代號5: � 魔力球偵測 - 抓取魔球「有魔」時的顏色 ⭐`n"
        教學內容 .= "       (右下角藍色魔力球，藍色消失時自動喝魔水)`n`n"
        
        教學內容 .= "代號6: 🩸 血條喝水偵測 - 抓取血條「空血」時的顏色`n"
        教學內容 .= "       (頭上血條消失時的底色，用於自動喝血水)`n`n"
        
        教學內容 .= "代號7: 🏠 血條返角偵測 - 抓取血條「空血」時的顏色`n"
        教學內容 .= "       (同代號6，但用於低血量返回角色選單)`n`n"
        
        教學內容 .= "代號8: ⚡ 血條穿透偵測 - 護盾被穿透時的血量偵測`n"
        教學內容 .= "       (能量護盾存在但血量不足時的顏色)`n`n"
        
        教學內容 .= "代號9: 🔄 穿透返角偵測 - 護盾被穿透時的低血返角`n"
        教學內容 .= "       (同代號8，但用於緊急返回角色選單)`n`n"
        
        教學內容 .= "💡 抓取技巧:`n"
        教學內容 .= "• 血條: 座標越接近滿血位置 = 提早觸發 (約80-90%血量時喝水)`n"
        教學內容 .= "• 血球: 座標越接近滿血位置 = 提早觸發 (血球稍少就補充)`n"
        教學內容 .= "• 魔球: 座標越接近滿魔位置 = 提早觸發 (魔力稍少就補充)`n`n"
        
        教學內容 .= "⚠️ 注意事項:`n"
        教學內容 .= "• 必須設置: 代號1(場景)、代號2(對話框1)、代號3(對話框2)，系統才能正常運作`n"
        教學內容 .= "• 建議設置: 代號4(血球)、代號5(魔球)、代號6(血條喝水)`n"
        教學內容 .= "• 可重複抓取同一代號來調整觸發時機`n"
        教學內容 .= "• 🎯 準心功能: 系統會在抓取的座標位置顯示十字準心，確認位置正確性`n"
        教學內容 .= "• 如準心位置不對，按 [ESC] 關閉面板，重新定位滑鼠後再按 [F7]"
        
        ; 🔥 創建專門的教學視窗
        教學GUI := Gui("+Resize", "🎯 座標抓取完整教學")
        教學GUI.BackColor := "0xF0F8FF"
        教學GUI.SetFont("s11", "Microsoft JhengHei")
        
        教學GUI.Add("Edit", "x10 y10 w580 h450 ReadOnly VScroll", 教學內容)
        
        ; 按鈕區域
        教學GUI.Add("Button", "x150 y470 w120 h30", "🎯 立即抓取座標").OnEvent("Click", 立即抓取座標)
        教學GUI.Add("Button", "x280 y470 w100 h30", "確定").OnEvent("Click", (*) => 教學GUI.Destroy())
        
        ; 🔥 支援ESC關閉
        教學GUI.OnEvent("Escape", (*) => 教學GUI.Destroy())
        
        教學GUI.Show("w600 h510")
        
        ; 立即抓取座標的處理函數
        立即抓取座標(*) {
            ; 🔥 關閉教學GUI和狀態偵測GUI，避免阻擋用戶畫面
            global 當前狀態偵測GUI
            教學GUI.Destroy()
            if (當前狀態偵測GUI != "" && IsObject(當前狀態偵測GUI)) {
                try {
                    當前狀態偵測GUI.Destroy()
                    當前狀態偵測GUI := ""
                } catch {
                    ; GUI可能已經被銷毀
                }
            }
            
            ; 🔥 顯示詳細引導說明
            MsgBox("🎯 智能偵測系統 - 快速設置`n`n" .
                   "📍 操作步驟：`n" .
                   "1. 將滑鼠移到要偵測的位置`n" .
                   "2. 按下 [Win+C] 或 [F7] 抓取座標`n" .
                   "3. 輸入對應代號 (1-9)`n" .
                   "4. 🎯 系統會顯示準心標示座標位置`n" .
                   "5. 位置不對請按 [ESC] 重新定位`n`n" .
                   "🎮 必須設置：`n" .
                   "• 代號1: 場景偵測 (必須設置)`n" .
                   "• 代號2: 對話框1偵測 (必須設置)`n" .
                   "• 代號3: 對話框2偵測 (必須設置)`n`n" .
                   "🎯 建議設置：`n" .
                   "• 代號4: 血球偵測 (左下紅球)`n" .
                   "• 代號5: 魔球偵測 (右下藍球)`n" .
                   "• 代號6: 血條喝水偵測 (上方血條)`n`n" .
                   "💡 準心功能：顯示當前抓取的精確座標位置", 
                   "座標抓取指南", 0x40)
            
            ShowToolTip("🎯 請將滑鼠指向要偵測的位置，然後按 [Win+C] 或 [F7]", 5000, 1)
        }
        
    } catch Error as err {
        ShowToolTip("教學顯示失敗: " . err.message, 3000, 1)
    }
}

; 🔥 檢查設置狀態並顯示動態信息
檢查設置狀態並顯示() {
    global
    
    ; 收集設置狀態
    設置狀態 := Map()
    未完成項目 := Array()
    已完成項目 := Array()
    
    ; 檢查各項設置
    ; 場景偵測點 (必須)
    if (顏色4_X != "error" && 顏色4_Y != "error") {
        已完成項目.Push("✅ 場景偵測點 (必須)")
        設置狀態["場景偵測"] := true
    } else {
        未完成項目.Push("❌ 場景偵測點 (必須)")
        設置狀態["場景偵測"] := false
    }
    
    ; 血條偵測點
    if (顏色1_X != "error" && 顏色1_Y != "error") {
        已完成項目.Push("✅ 血條偵測點")
        設置狀態["血條偵測"] := true
    } else {
        未完成項目.Push("⚪ 血條偵測點 (建議)")
        設置狀態["血條偵測"] := false
    }
    
    ; 魔球偵測點
    if (顏色3_X != "error" && 顏色3_Y != "error") {
        已完成項目.Push("✅ 魔球偵測點")
        設置狀態["魔球偵測"] := true
    } else {
        未完成項目.Push("⚪ 魔球偵測點 (建議)")
        設置狀態["魔球偵測"] := false
    }
    
    ; 血球池偵測點
    if (顏色9_X != "error" && 顏色9_Y != "error") {
        已完成項目.Push("✅ 血球池偵測點")
        設置狀態["血球池偵測"] := true
    } else {
        未完成項目.Push("⚪ 血球池偵測點 (選用)")
        設置狀態["血球池偵測"] := false
    }
    
    ; 穿透偵測點
    if (顏色7_X != "error" && 顏色7_Y != "error") {
        已完成項目.Push("✅ 穿透偵測點")
        設置狀態["穿透偵測"] := true
    } else {
        未完成項目.Push("⚪ 穿透偵測點 (進階)")
        設置狀態["穿透偵測"] := false
    }
    
    ; 穿透返角點
    if (顏色8_X != "error" && 顏色8_Y != "error") {
        已完成項目.Push("✅ 穿透返角點")
        設置狀態["穿透返角"] := true
    } else {
        未完成項目.Push("⚪ 穿透返角點 (進階)")
        設置狀態["穿透返角"] := false
    }
    
    ; 生成狀態信息
    狀態信息 := "🎯 F10 功能設置狀態檢查`n`n"
    
    ; 顯示已完成項目
    if (已完成項目.Length > 0) {
        狀態信息 .= "【已完成設置】`n"
        for item in 已完成項目 {
            狀態信息 .= item . "`n"
        }
        狀態信息 .= "`n"
    }
    
    ; 顯示未完成項目
    if (未完成項目.Length > 0) {
        狀態信息 .= "【待完成設置】`n"
        for item in 未完成項目 {
            狀態信息 .= item . "`n"
        }
        狀態信息 .= "`n"
    }
    
    ; 顯示功能可用性
    if (設置狀態["場景偵測"]) {
        狀態信息 .= "🟢 基礎功能：可使用 (場景偵測已設置)`n"
        
        if (設置狀態["血條偵測"] || 設置狀態["魔球偵測"] || 設置狀態["血球池偵測"]) {
            狀態信息 .= "🔵 智能喝水：可使用 (已設置喝水偵測點)`n"
        } else {
            狀態信息 .= "🟡 智能喝水：建議設置血條/魔球/血球池偵測點`n"
        }
        
        if (設置狀態["穿透偵測"] || 設置狀態["穿透返角"]) {
            狀態信息 .= "🔥 進階功能：可使用 (已設置穿透偵測點)`n"
        } else {
            狀態信息 .= "⚪ 進階功能：設置穿透偵測點以啟用`n"
        }
    } else {
        狀態信息 .= "🚨 無法使用 F10 功能：請先設置場景偵測點`n"
    }
    
    狀態信息 .= "`n💡 快速設置：[Win+Z] → 💚 狀態偵測設置 → 完成座標設置"
    
    ; 顯示對話框
    result := MsgBox(狀態信息, "F10 功能設置狀態", 0x40 + 0x1)
    
    ; 如果用戶點擊確定且場景偵測未設置，則打開設置界面
    if (result == "OK" && !設置狀態["場景偵測"]) {
        SetTimer(() => 狀態設置說明(), -500)
    }
    
    return 設置狀態
}

; 驗證設置值的有效性
驗證設置值有效性() {
    global
    local 問題列表 := Array()
    local 有問題 := false
    
    ; 驗證座標值範圍 (螢幕解析度檢查)
    螢幕寬度 := A_ScreenWidth
    螢幕高度 := A_ScreenHeight
    
    ; 檢查顏色偵測座標
    loop 9 {
        xVar := "顏色" . A_Index . "_X"
        yVar := "顏色" . A_Index . "_Y"
        
        if (%xVar% != "error" && %yVar% != "error") {
            x := %xVar%
            y := %yVar%
            
            if (x < 0 || x > 螢幕寬度 || y < 0 || y > 螢幕高度) {
                問題列表.Push("偵測點" . A_Index . "座標超出螢幕範圍")
                有問題 := true
            }
        }
    }
    
    ; 檢查背包座標
    if (背包左上_X != "error" && 背包左上_Y != "error" && 背包右下_X != "error" && 背包右下_Y != "error") {
        if (背包左上_X >= 背包右下_X || 背包左上_Y >= 背包右下_Y) {
            問題列表.Push("背包座標設定不正確 (左上角應小於右下角)")
            有問題 := true
        }
        
        if (背包左上_X < 0 || 背包左上_X > 螢幕寬度 || 背包左上_Y < 0 || 背包左上_Y > 螢幕高度 ||
            背包右下_X < 0 || 背包右下_X > 螢幕寬度 || 背包右下_Y < 0 || 背包右下_Y > 螢幕高度) {
            問題列表.Push("背包座標超出螢幕範圍")
            有問題 := true
        }
    }
    
    ; 驗證數值型參數
    if (F1按鍵間隔 != "error") {
        if (F1按鍵間隔 < 10 || F1按鍵間隔 > 1000) {
            問題列表.Push("F1按鍵間隔設定不合理 (建議10-1000ms)")
            有問題 := true
        }
    }
    
    if (F2重複間隔 != "error") {
        if (F2重複間隔 < 50 || F2重複間隔 > 2000) {
            問題列表.Push("F2重複間隔設定不合理 (建議50-2000ms)")
            有問題 := true
        }
    }
    
    if (滑鼠連點速度 != "error") {
        if (滑鼠連點速度 < 1 || 滑鼠連點速度 > 100) {
            問題列表.Push("滑鼠連點速度設定不合理 (建議1-100)")
            有問題 := true
        }
    }
    
    ; 驗證循環技能設定
    loop 5 {
        時間變數 := "循環技能時間" . A_Index
        if (%時間變數% != "error") {
            if (%時間變數% < 100 || %時間變數% > 30000) {
                問題列表.Push("循環技能" . A_Index . "時間設定不合理 (建議100-30000ms)")
                有問題 := true
            }
        }
    }
    
    return {有問題: 有問題, 問題列表: 問題列表}
}

; 🔥 檢查F7背包座標設置狀態並顯示動態信息
檢查F7座標設置狀態() {
    global
    
    ; 收集設置狀態
    設置狀態 := Map()
    未完成項目 := Array()
    已完成項目 := Array()
    
    ; 檢查背包座標設置
    if (背包左上_X != "error" && 背包左上_Y != "error" && 背包右下_X != "error" && 背包右下_Y != "error") {
        已完成項目.Push("✅ 個人背包座標")
        設置狀態["個人背包"] := true
    } else {
        未完成項目.Push("❌ 個人背包座標 (必須)")
        設置狀態["個人背包"] := false
    }
    
    ; 檢查對方背包座標設置
    if (對方背包左上_X != "error" && 對方背包左上_Y != "error" && 對方背包右下_X != "error" && 對方背包右下_Y != "error") {
        已完成項目.Push("✅ 對方背包座標")
        設置狀態["對方背包"] := true
    } else {
        未完成項目.Push("⚪ 對方背包座標 (交易用)")
        設置狀態["對方背包"] := false
    }
    
    ; 檢查交易按鈕座標
    if (接受交易_X != "error" && 接受交易_Y != "error") {
        已完成項目.Push("✅ 接受交易按鈕")
        設置狀態["接受交易"] := true
    } else {
        未完成項目.Push("⚪ 接受交易按鈕 (交易用)")
        設置狀態["接受交易"] := false
    }
    
    ; 生成狀態信息
    狀態信息 := "🎒 F7 背包座標設置狀態檢查`n`n"
    
    ; 顯示已完成項目
    if (已完成項目.Length > 0) {
        狀態信息 .= "【已完成設置】`n"
        for item in 已完成項目 {
            狀態信息 .= item . "`n"
        }
        狀態信息 .= "`n"
    }
    
    ; 顯示未完成項目
    if (未完成項目.Length > 0) {
        狀態信息 .= "【待完成設置】`n"
        for item in 未完成項目 {
            狀態信息 .= item . "`n"
        }
        狀態信息 .= "`n"
    }
    
    ; 顯示功能可用性
    if (設置狀態["個人背包"]) {
        狀態信息 .= "🟢 基本功能：可使用 (個人背包座標已設置)`n"
        
        if (設置狀態["對方背包"] && 設置狀態["接受交易"]) {
            狀態信息 .= "🔵 交易功能：可使用 (交易相關座標已設置)`n"
        } else {
            狀態信息 .= "⚪ 交易功能：需設置對方背包和交易按鈕座標`n"
        }
    } else {
        狀態信息 .= "🚨 無法使用 F7 相關功能：請先設置個人背包座標`n"
    }
    
    狀態信息 .= "`n💡 設置提示：使用 F7 在背包左上角和右下角抓取座標"
    
    ; 顯示 ToolTip 而不是對話框（避免影響後續座標抓取）
    ShowToolTip(狀態信息, 4000, 2)
    
    return 設置狀態
}

; 🔥 檢查Win+C偵測點設置狀態並顯示動態信息
檢查WinC偵測點設置狀態() {
    global
    
    ; 收集設置狀態
    設置狀態 := Map()
    未完成項目 := Array()
    已完成項目 := Array()
    
    ; 定義偵測點名稱和重要性
    偵測點資訊 := Map(
        "1", {name: "場景變化偵測", importance: "必須", desc: "遊戲狀態判斷"},
        "2", {name: "對話框1偵測", importance: "必須", desc: "Enter對話框偵測"},
        "3", {name: "對話框2偵測", importance: "必須", desc: "位移對話框偵測"},
        "4", {name: "血球池偵測點", importance: "推薦", desc: "血球池監控"},
        "5", {name: "魔力球偵測點", importance: "推薦", desc: "魔力監控"},
        "6", {name: "血條喝水偵測點", importance: "選用", desc: "角色血條監控"},
        "7", {name: "血條返角偵測點", importance: "選用", desc: "低血條返角監控"},
        "8", {name: "血條穿透偵測點", importance: "進階", desc: "混傷穿透監控"},
        "9", {name: "穿透返角偵測點", importance: "進階", desc: "混傷穿透返角監控"}
    )
    
    ; 檢查各偵測點設置狀態
    for pointID, info in 偵測點資訊 {
        ; 動態構建變數名稱
        xVar := "顏色" . pointID . "_X"
        yVar := "顏色" . pointID . "_Y"
        
        ; 檢查是否已設置（使用 %% 動態變數引用）
        if (%xVar% != "error" && %yVar% != "error") {
            switch info.importance {
                case "必須":
                    已完成項目.Push("✅ " . info.name . " (" . info.importance . ")")
                case "建議":
                    已完成項目.Push("✅ " . info.name . " (" . info.importance . ")")
                case "選用", "進階":
                    已完成項目.Push("✅ " . info.name . " (" . info.importance . ")")
            }
            設置狀態[pointID] := true
        } else {
            switch info.importance {
                case "必須":
                    未完成項目.Push("❌ " . info.name . " (" . info.importance . ")")
                case "建議":
                    未完成項目.Push("⚪ " . info.name . " (" . info.importance . ")")
                case "選用", "進階":
                    未完成項目.Push("⚪ " . info.name . " (" . info.importance . ")")
            }
            設置狀態[pointID] := false
        }
    }
    
    ; 生成狀態信息
    狀態信息 := "🎯 Win+C 偵測點設置狀態檢查`n`n"
    
    ; 顯示已完成項目
    if (已完成項目.Length > 0) {
        狀態信息 .= "【已完成設置】`n"
        for item in 已完成項目 {
            狀態信息 .= item . "`n"
        }
        狀態信息 .= "`n"
    }
    
    ; 顯示未完成項目
    if (未完成項目.Length > 0) {
        狀態信息 .= "【待完成設置】`n"
        for item in 未完成項目 {
            狀態信息 .= item . "`n"
        }
        狀態信息 .= "`n"
    }
    
    ; 顯示功能可用性分析
    必須偵測點完成 := 設置狀態["4"] && 設置狀態["5"] && 設置狀態["6"]
    建議偵測點完成 := 設置狀態["1"] || 設置狀態["2"] || 設置狀態["3"] || 設置狀態["9"]
    進階偵測點完成 := 設置狀態["7"] || 設置狀態["8"]
    
    if (必須偵測點完成) {
        狀態信息 .= "🟢 基礎功能：可使用 (必須偵測點已設置)`n"
        
        if (建議偵測點完成) {
            狀態信息 .= "🔵 智能監控：可使用 (建議偵測點已設置)`n"
        } else {
            狀態信息 .= "🟡 智能監控：建議設置血條/魔球/血球偵測點`n"
        }
        
        if (進階偵測點完成) {
            狀態信息 .= "🔥 進階功能：可使用 (穿透偵測點已設置)`n"
        } else {
            狀態信息 .= "⚪ 進階功能：設置穿透偵測點以啟用`n"
        }
    } else {
        狀態信息 .= "🚨 無法使用偵測功能：請先設置場景偵測點(1)、對話框1偵測(2)和對話框2偵測(3)`n"
    }
    
    狀態信息 .= "`n💡 設置提示：使用 Win+C 在指定位置抓取偵測點座標 (1-9)"
    
    ; 顯示 ToolTip 而不是對話框（避免影響後續座標抓取）
    ShowToolTip(狀態信息, 4000, 2)
    
    return 設置狀態
}

; ========================== F鍵功能系統 ==========================

; F1快速組合功能
F1::
{
    global
    if (!WinActive("Path of Exile") && !WinActive("Path of Exile 2")) {
        return
    }
    
    if (Toolbutton = 1) {
        ShowToolTip("文字輸入模式中，快速組合暫停", 1000, 1)
        return
    }
    
    ; 執行快速組合
    執行F1組合()
}

; 執行F1組合
執行F1組合() {
    global
    
    if (F1功能模式 = 1 && F1自訂序列) {
        ; 自訂序列模式
        按鍵列表 := StrSplit(F1自訂序列, "-")
        for index, 按鍵 in 按鍵列表 {
            if 按鍵 {
                Send(按鍵)
                Sleep(F1按鍵間隔)
            }
        }
        ShowToolTip("✅ F1自訂序列已執行", 1500, 1)
    } else {
        ; 傳統模式
        switch F1功能模式 {
            case 0:
                Send("2")
                Sleep(F1按鍵間隔)
                Send("3")
                Sleep(F1按鍵間隔)
                Send("4")
                Sleep(F1按鍵間隔)
                Send("5")
                Sleep(F1按鍵間隔)
                Send("q")
                ShowToolTip("✅ F1標準組合已執行", 1500, 1)
            case 2:
                ; 僅藥水
                Send("2")
                Sleep(F1按鍵間隔)
                Send("3")
                Sleep(F1按鍵間隔)
                Send("4")
                Sleep(F1按鍵間隔)
                Send("5")
                ShowToolTip("✅ F1藥水組合已執行", 1500, 1)
        }
    }
}

; F2暫離/勿擾/自動回復模式
F2::
{
    global
    if (!WinActive("Path of Exile") && !WinActive("Path of Exile 2")) {
        return
    }
    
    if (Toolbutton = 1) {
        ShowToolTip("文字輸入模式中，F2功能暫停", 1000, 1)
        return
    }
    
    ; 打開回復模式設定GUI
    Show_ReplyModeGui()
}

; F3技能循環功能
F3::
{
    global
    if (!WinActive("Path of Exile") && !WinActive("Path of Exile 2")) {
        return
    }
    
    if (Toolbutton = 1) {
        ShowToolTip("文字輸入模式中，F3功能暫停", 1000, 1)
        return
    }
    
    執行F3循環()
}

; 執行F3循環
執行F3循環() {
    global
    
    if (F3循環序列) {
        序列列表 := StrSplit(F3循環序列, "-")
        if (序列列表.Length > 0) {
            ; 更新循環位置
            if (!F3當前位置 || F3當前位置 > 序列列表.Length) {
                F3當前位置 := 1
            }
            
            當前按鍵 := 序列列表[F3當前位置]
            if 當前按鍵 {
                Send(當前按鍵)
                ShowToolTip("✅ F3循環: " . 當前按鍵 . " (" . F3當前位置 . "/" . 序列列表.Length . ")", 1000, 1)
                F3當前位置++
            }
        }
    }
}

; ========================== 技能監聽系統 ==========================

; 進階藥劑系統技能監聽
監聽技能觸發(按下的技能) {
    global
    
    ; 檢查遊戲視窗和相關狀態
    if (!檢查遊戲視窗() || Toolbutton = 1) {
        return  ; 不在遊戲視窗或文字模式時不執行
    }
    
    ; 檢查高級功能是否開啟
    if (Autodrinkbutton = "1") {
        ; 執行技能連段功能
        執行技能連段(StrLower(按下的技能))
        
        ; 執行地雷功能
        處理地雷觸發(按下的技能)
    }
}

; Q鍵監聽
~q::
{
    global
    if (WinActive("Path of Exile") || WinActive("Path of Exile 2")) {
        監聽技能觸發("Q")
    }
}

; W鍵監聽  
~w::
{
    global
    if (WinActive("Path of Exile") || WinActive("Path of Exile 2")) {
        監聽技能觸發("W")
    }
}

; E鍵監聽
~e::
{
    global
    if (WinActive("Path of Exile") || WinActive("Path of Exile 2")) {
        監聽技能觸發("E")
    }
}

; R鍵監聽
~r::
{
    global
    if (WinActive("Path of Exile") || WinActive("Path of Exile 2")) {
        監聽技能觸發("R")
    }
}

; T鍵監聽
~t::
{
    global
    if (WinActive("Path of Exile") || WinActive("Path of Exile 2")) {
        監聽技能觸發("T")
    }
}

; ========================== 按鍵釋放監聽 (地雷功能) ==========================

; Q鍵釋放監聽
~q up::
{
    global
    if (WinActive("Path of Exile") || WinActive("Path of Exile 2")) {
        釋放地雷長按("Q")
    }
}

; W鍵釋放監聽
~w up::
{
    global
    if (WinActive("Path of Exile") || WinActive("Path of Exile 2")) {
        釋放地雷長按("W")
    }
}

; E鍵釋放監聽
~e up::
{
    global
    if (WinActive("Path of Exile") || WinActive("Path of Exile 2")) {
        釋放地雷長按("E")
    }
}

; R鍵釋放監聽
~r up::
{
    global
    if (WinActive("Path of Exile") || WinActive("Path of Exile 2")) {
        釋放地雷長按("R")
    }
}

; T鍵釋放監聽
~t up::
{
    global
    if (WinActive("Path of Exile") || WinActive("Path of Exile 2")) {
        釋放地雷長按("T")
    }
}

; ========================== 互動式顏色抓取系統 ==========================

; ========================== 通用顏色預覽模組 ==========================

; 全域變數 - 通用顏色預覽模組
global 通用顏色預覽GUI := ""
global 通用顏色方塊控制項 := ""
global 通用顏色文字控制項 := ""
global 通用標題文字 := ""
global 通用操作提示 := ""
global 通用上次顏色 := ""

; 創建通用顏色預覽面板
; 參數: title (標題), helpText (操作提示), x (位置X), y (位置Y)
創建通用顏色預覽面板(title := "🎯 即時顏色抓取", helpText := "⏎ Enter 確認選擇    ⎋ Esc 取消", x := "", y := "") {
    global 通用顏色預覽GUI, 通用顏色方塊控制項, 通用顏色文字控制項, 通用標題文字, 通用操作提示
    
    ; 如果已存在，先銷毀
    銷毀通用顏色預覽面板()
    
    ; 設定預設位置
    if (x = "") {
        x := A_ScreenWidth - 320
    }
    if (y = "") {
        y := 50
    }
    
    try {
        通用顏色預覽GUI := Gui("+AlwaysOnTop -MaximizeBox -MinimizeBox +LastFound +ToolWindow", title)
        通用顏色預覽GUI.BackColor := "0x2D2D2D"  ; 深灰色背景
        通用顏色預覽GUI.MarginX := 15
        通用顏色預覽GUI.MarginY := 15
        
        ; 添加標題
        通用標題文字 := 通用顏色預覽GUI.Add("Text", "x15 y10 w250 h25 Center c0xFFFFFF", title)
        通用標題文字.SetFont("s12 Bold", "Microsoft YaHei UI")
        
        ; 創建顏色方塊容器（帶邊框）
        顏色容器 := 通用顏色預覽GUI.Add("Text", "x15 y40 w50 h50 Border")
        顏色容器.Opt("Background0x404040")  ; 容器背景
        
        ; 添加顏色方塊控制項（初始顏色設為黑色）
        通用顏色方塊控制項 := 通用顏色預覽GUI.Add("Text", "x18 y43 w44 h44 Border Background0x000000")
        
        ; 添加顏色信息文字區域
        通用顏色文字控制項 := 通用顏色預覽GUI.Add("Text", "x75 y45 w190 h85 c0xE0E0E0", 
            "座標: (0, 0)`n" .
            "顏色: 0x000000`n" .
            "RGB: (0, 0, 0)"
        )
        通用顏色文字控制項.SetFont("s10", "Consolas")
        
        ; 添加操作提示（帶樣式）
        通用操作提示 := 通用顏色預覽GUI.Add("Text", "x15 y135 w250 h30 Center c0xFFD700", helpText)
        通用操作提示.SetFont("s9 Bold", "Microsoft YaHei UI")
        
        ; 添加底部裝飾線
        裝飾線 := 通用顏色預覽GUI.Add("Text", "x15 y165 w250 h2")
        裝飾線.Opt("Background0x4CAF50")  ; 綠色裝飾線
        
        ; 顯示GUI並激活為前景視窗
        通用顏色預覽GUI.Show("x" . x . " y" . y . " w280 h180")
        
        ; 確保GUI成為活動視窗，讓遊戲視窗失去焦點
        try {
            WinActivate(通用顏色預覽GUI.Hwnd)
            ; 短暫延遲確保激活完成
            Sleep(50)
        } catch {
            ; 如果激活失敗，忽略錯誤
        }
        
        return true
    } catch {
        return false
    }
}

; 更新通用顏色預覽面板
; 參數: mx (滑鼠X), my (滑鼠Y), color (顏色值), 可選: 強制更新
更新通用顏色預覽面板(mx, my, color, forceUpdate := false) {
    global 通用顏色預覽GUI, 通用顏色方塊控制項, 通用顏色文字控制項, 通用上次顏色
    
    if (!IsObject(通用顏色預覽GUI)) {
        return false
    }
    
    ; 如果顏色沒有變化且非強制更新，不需要更新
    if (!forceUpdate && IsSet(通用上次顏色) && color = 通用上次顏色) {
        return true
    }
    
    通用上次顏色 := color
    
    ; 轉換顏色格式
    colorHex := "0x" . Format("{:06X}", color)
    r := (color >> 16) & 0xFF
    g := (color >> 8) & 0xFF
    b := color & 0xFF
    
    try {
        ; 重新創建顏色方塊以更新顏色
        if (IsObject(通用顏色方塊控制項)) {
            try {
                通用顏色方塊控制項.Destroy()
            } catch {
            }
            通用顏色方塊控制項 := 通用顏色預覽GUI.Add("Text", "x18 y43 w44 h44 Border Background" . Format("0x{:06X}", color))
        }
        
        ; 更新文字內容
        if (IsObject(通用顏色文字控制項)) {
            通用顏色文字控制項.Text := "座標: (" . mx . ", " . my . ")`n" .
                "顏色: " . colorHex . "`n" .
                "RGB: (" . r . ", " . g . ", " . b . ")"
        }
        return true
    } catch {
        return false
    }
}

; 銷毀通用顏色預覽面板
銷毀通用顏色預覽面板() {
    global 通用顏色預覽GUI, 通用顏色方塊控制項, 通用顏色文字控制項, 通用標題文字, 通用操作提示, 通用上次顏色
    
    try {
        if (IsObject(通用顏色預覽GUI)) {
            通用顏色預覽GUI.Destroy()
        }
    } catch {
    }
    
    ; 重置所有變數
    通用顏色預覽GUI := ""
    通用顏色方塊控制項 := ""
    通用顏色文字控制項 := ""
    通用標題文字 := ""
    通用操作提示 := ""
    通用上次顏色 := ""
}

; 更新通用顏色預覽面板的操作提示
更新通用顏色預覽操作提示(helpText) {
    global 通用操作提示
    
    try {
        if (IsObject(通用操作提示)) {
            通用操作提示.Text := helpText
            return true
        }
    } catch {
    }
    return false
}

; ========================== F8專用顏色抓取（使用通用模組）==========================

; 更新顏色監控
更新顏色監控() {
    global 顏色抓取中
    
    if (!顏色抓取中) {
        return
    }
    
    ; 獲取當前滑鼠位置和顏色
    MouseGetPos(&mx, &my)
    currentColor := PixelGetColor(mx, my)
    
    ; 使用通用顏色預覽模組
    if (!IsObject(通用顏色預覽GUI)) {
        ; 第一次創建面板
        創建通用顏色預覽面板("🎯 F8 智能拾取顏色抓取", "⏎ Enter 確認選擇    ⎋ Esc 取消")
    }
    
    ; 更新顏色預覽
    更新通用顏色預覽面板(mx, my, currentColor)
}

; 確認顏色抓取
確認顏色抓取(*) {
    global 顏色抓取中, 當前顏色輸入控制項, 拾取目標顏色
    
    if (!顏色抓取中) {
        return
    }
    
    ; 獲取當前滑鼠位置的顏色
    MouseGetPos(&mx, &my)
    selectedColor := PixelGetColor(mx, my)
    colorHex := "0x" . Format("{:06X}", selectedColor)  ; 統一使用0x格式
    
    ; 保存顏色到全域變數
    拾取目標顏色 := colorHex
    
    ; 更新輸入控制項
    if (當前顏色輸入控制項) {
        當前顏色輸入控制項.Text := colorHex
    }
    
    ; 顯示成功提示
    ShowSuccessIndicator(mx, my, "顏色已確認: " . colorHex)
    ShowToolTip("✅ 顏色已成功抓取: " . colorHex, 3000, 2)
    
    ; 停止顏色抓取
    停止顏色抓取()
    
    ; GUI保持顯示，無需重新Show
    ; if (當前拾取設置GUI) {
    ;     當前拾取設置GUI.Show()
    ; }
}

; 取消顏色抓取
取消顏色抓取(*) {
    global 顏色抓取中, 當前拾取設置GUI
    
    if (!顏色抓取中) {
        return
    }
    
    ShowToolTip("❌ 顏色抓取已取消", 2000, 1)
    
    ; 停止顏色抓取
    停止顏色抓取()
    
    ; GUI保持顯示，無需重新Show
    ; if (當前拾取設置GUI) {
    ;     當前拾取設置GUI.Show()
    ; }
}

; 停止顏色抓取
停止顏色抓取() {
    global 顏色抓取中, 顏色抓取計時器, 拾取設置GUI
    
    顏色抓取中 := false
    
    ; 停止計時器
    if (顏色抓取計時器) {
        SetTimer(顏色抓取計時器, 0)
        顏色抓取計時器 := ""
    }
    
    ; 關閉ToolTip
    ToolTip()
    
    ; 清理通用顏色預覽面板
    銷毀通用顏色預覽面板()
    
    ; 解除熱鍵綁定
    try {
        Hotkey("Enter", 確認顏色抓取, "Off")
        Hotkey("Escape", 取消顏色抓取, "Off")
    } catch {
        ; 忽略錯誤
    }
    
    ; 重新顯示主GUI並激活
    try {
        if (拾取設置GUI) {
            拾取設置GUI.Show()
            ; 確保拾取設置GUI重新成為活動視窗
            WinActivate(拾取設置GUI.Hwnd)
        }
    } catch {
        ; 如果GUI已被銷毀，重新創建
        try {
            顯示智能拾取設置GUI()
        } catch {
            ; 忽略重新創建錯誤
        }
    }
}

; ======================================================================================================
; 🎯 快速交易熱鍵系統
; ======================================================================================================

; End鍵 - 快速申請組隊
End_快速組隊() {
    if (!檢查遊戲視窗()) {
        return
    }
    
    if (快速組隊提醒 = "關閉" && 使用者類型 = "已贊助") {
        ; 直接組隊，不使用提醒視窗
        獲取對方ID()
        global 移除後完好的ID
        A_Clipboard := "/invite " . 移除後完好的ID
        
        if (WinExist("Path of Exile 2")) {
            WinActivate("Path of Exile 2")
        } else {
            WinActivate("Path of Exile")
        }
        Send("{Enter}")
        Send("^v")
        Sleep(50)
        Send("{Enter}")
        ShowToolTip("✅ 快速組隊: " . 移除後完好的ID, 3000, 3)
    } else {
        ; 組隊前提醒
        獲取對方ID()
        global 移除後完好的ID
        result := MsgBox("即將組隊的玩家是 「" . 移除後完好的ID . "」`n`n確定組隊嗎？", "快速組隊確認", "YesNo 4096")
        
        if (result = "Yes") {
            A_Clipboard := "/invite " . 移除後完好的ID
            if (WinExist("Path of Exile 2")) {
                WinActivate("Path of Exile 2")
            } else {
                WinActivate("Path of Exile")
            }
            Send("^v")
            Sleep(50)
            Send("{Enter}")
            ShowToolTip("✅ 快速組隊: " . 移除後完好的ID, 3000, 3)
        } else {
            if (WinExist("Path of Exile 2")) {
                WinActivate("Path of Exile 2")
            } else {
                WinActivate("Path of Exile")
            }
            ShowToolTip("❌ 組隊已取消", 2000, 1)
        }
    }
}

; Home鍵 - 快速申請交易
Home_快速交易() {
    if (!檢查遊戲視窗()) {
        return
    }
    
    if (快速交易提醒 = "關閉" && 使用者類型 = "已贊助") {
        ; 直接交易，不使用提醒視窗
        獲取對方ID()
        global 移除後完好的ID
        A_Clipboard := "/tradewith " . 移除後完好的ID
        
        if (WinExist("Path of Exile 2")) {
            WinActivate("Path of Exile 2")
        } else {
            WinActivate("Path of Exile")
        }
        Send("{Enter}")
        Send("^v")
        Sleep(50)
        Send("{Enter}")
        ShowToolTip("✅ 快速交易: " . 移除後完好的ID, 3000, 3)
    } else {
        ; 交易前提醒
        獲取對方ID()
        global 移除後完好的ID
        result := MsgBox("即將交易的玩家是 「" . 移除後完好的ID . "」`n`n確定交易嗎？", "快速交易確認", "YesNo 4096")
        
        if (result = "Yes") {
            A_Clipboard := "/tradewith " . 移除後完好的ID
            if (WinExist("Path of Exile 2")) {
                WinActivate("Path of Exile 2")
            } else {
                WinActivate("Path of Exile")
            }
            Send("^v")
            Sleep(50)
            Send("{Enter}")
            ShowToolTip("✅ 快速交易: " . 移除後完好的ID, 3000, 3)
        } else {
            if (WinExist("Path of Exile 2")) {
                WinActivate("Path of Exile 2")
            } else {
                WinActivate("Path of Exile")
            }
            ShowToolTip("❌ 交易已取消", 2000, 1)
        }
    }
}

; PgUp鍵 - 確認交易欄位
PgUp_確認交易欄位() {
    if (!檢查遊戲視窗()) {
        return
    }
    
    ; 檢查是否已設置對方背包座標
    if (對方背包左上_X = "error" || 對方背包右下_X = "error") {
        ShowToolTip("❌ 尚未設定快速交易座標，請先使用 F7 設定", 3000, 1)
        MsgBox("尚未設定快速交易，確認對方背包60格欄位座標。`n`n請隨意尋找 NPC 點擊「販賣物品」打開，使用 F7 設定。", "座標設定提醒", "0x40")
        return
    }
    
    ; 執行掃描對方背包檢查
    掃描對方背包()
    ShowToolTip("✅ 交易欄位確認完成", 2000, 3)
}

; PgDn鍵 - 接受交易
PgDn_接受交易() {
    if (!檢查遊戲視窗()) {
        return
    }
    
    ; 檢查是否已設置接受交易座標
    if (接受交易_X = "error" || 接受交易_Y = "error") {
        ShowToolTip("❌ 尚未設定接受交易座標，請先使用 F7 設定", 3000, 1)
        MsgBox("尚未設定快速交易，「接受」交易座標。`n`n請隨意尋找 NPC 點擊「販賣物品」打開，使用 F7 設定。", "座標設定提醒", "0x40")
        return
    }
    
    ; 點擊接受交易
    Click(接受交易_X, 接受交易_Y)
    ShowToolTip("✅ 交易已接受", 2000, 3)
}

; 獲取對方ID (從聊天窗口)
獲取對方ID() {
    global 移除後完好的ID
    
    if (WinExist("Path of Exile 2")) {
        WinActivate("Path of Exile 2")
    } else {
        WinActivate("Path of Exile")
    }
    Send("^{Enter}")
    Sleep(50)
    Send("^a")
    Sleep(50)
    Send("^c")
    Sleep(50)
    Send("{Enter}")
    Sleep(100)
    
    ; 取得並處理對方ID
    暫存對方ID := A_Clipboard
    對方ID := 暫存對方ID
    
    ; 清除ID前面的@符號
    移除後完好的ID := StrReplace(對方ID, "@", "")
    移除後完好的ID := Trim(移除後完好的ID)
}

; 掃描對方背包 (自動檢查對方背包物品)
掃描對方背包() {
    global 對方背包左上_X, 對方背包左上_Y, 對方背包右下_X, 對方背包右下_Y
    
    ; 計算背包格子參數
    掃描水平數量 := 12
    掃描垂直數量 := 5
    背包每格寬 := Floor((對方背包右下_X - 對方背包左上_X) / 掃描水平數量)
    背包每格高 := Floor((對方背包右下_Y - 對方背包左上_Y) / 掃描垂直數量)
    
    ShowToolTip("開始掃描對方背包... (按住右鍵可中斷)", 2000, 1)
    
    ; 逐格自動檢查背包
    Loop 掃描水平數量 {
        PosX := 對方背包左上_X + (背包每格寬 * (A_Index - 1)) + (背包每格寬 // 2)
        
        ; 檢查是否按住右鍵中斷
        if (GetKeyState("RButton", "P")) {
            ShowToolTip("🛑 掃描對方背包已被右鍵中斷", 2000, 1)
            return
        }
        
        Loop 掃描垂直數量 {
            PosY := 對方背包左上_Y + (背包每格高 * (A_Index - 1)) + (背包每格高 // 2)
            MouseMove(PosX, PosY, 0)
            Sleep(50)
            
            ; 檢查是否按住右鍵中斷
            if (GetKeyState("RButton", "P")) {
                ShowToolTip("🛑 掃描對方背包已被右鍵中斷", 2000, 1)
                return
            }
        }
    }
    
    ShowToolTip("✅ 對方背包掃描完成", 2000, 1)
}

; 快速交易設置說明
快速交易設置說明(*) {
    MsgBox("🎯 快速交易熱鍵系統說明`n`n" .
           "📋 功能說明：`n" .
           "• [End] 鍵 → 快速申請組隊`n" .
           "• [Home] 鍵 → 快速申請交易`n" .
           "• [PgUp] 鍵 → 確認交易欄位 (檢查對方60格背包)`n" .
           "• [PgDn] 鍵 → 接受交易`n`n" .
           "⚙️ 使用前準備：`n" .
           "1. 使用 F7 設定對方背包座標 (左上角、右下角)`n" .
           "2. 使用 F7 設定接受交易按鈕座標`n`n" .
           "💡 使用方式：`n" .
           "1. 在聊天視窗選擇要交易的玩家訊息`n" .
           "2. 按 [Home] 申請交易或 [End] 申請組隊`n" .
           "3. 交易視窗開啟後，按 [PgUp] 檢查對方物品`n" .
           "4. 確認無誤後，按 [PgDn] 接受交易`n`n" .
           "🔧 注意事項：`n" .
           "• 使用前請確保已正確設定座標`n" .
           "• 建議先與NPC測試座標設定是否正確", 
           "快速交易熱鍵說明", "0x40")
}

; ======================================================================================================
; 🖼️ 圖片指引功能
; ======================================================================================================

; 顯示背包設定圖片指引
顯示背包設定圖片() {
    try {
        if (!FileExist("image/F3圖例.png")) {
            ShowToolTip("❌ 找不到背包設定圖片", 3000, 1)
            return
        }
        
        ; 創建圖片顯示視窗
        圖片視窗 := Gui("+Resize", "背包座標設定圖例")
        圖片視窗.BackColor := "White"
        圖片視窗.Add("Text", "x20 y10 w400 h25 Center", "📷 背包座標設定參考圖例").SetFont("s12 Bold")
        圖片視窗.Add("Text", "x20 y40 w400 h25 Center", "請參考下圖設定背包左上角和右下角座標").SetFont("s10")
        
        ; 添加圖片控件
        圖片控件 := 圖片視窗.Add("Picture", "x20 y70", "image/F3圖例.png")
        
        ; 獲取圖片尺寸以調整視窗大小
        圖片寬度 := 400  ; 預設寬度
        圖片高度 := 300  ; 預設高度
        
        ; 調整視窗大小
        視窗寬度 := 圖片寬度 + 40
        視窗高度 := 圖片高度 + 180  ; 增加高度給按鈕留空間
        
        圖片視窗.Move(, , 視窗寬度, 視窗高度)
        
        ; 添加關閉按鈕，放在圖片下方而非覆蓋在圖片上
        關閉按鈕 := 圖片視窗.Add("Button", "x" . (視窗寬度/2 - 60) . " y" . (圖片高度 + 90) . " w120 h35", "關閉 (Esc)")
        關閉按鈕.OnEvent("Click", (*) => 圖片視窗.Destroy())
        關閉按鈕.SetFont("s10 Bold")
        
        ; 加入Esc鍵支援
        圖片視窗.OnEvent("Escape", (*) => 圖片視窗.Destroy())
        圖片視窗.OnEvent("Close", (*) => 圖片視窗.Destroy())
        
        ; 將視窗顯示在螢幕中央
        螢幕寬度 := SysGet(16)  ; 螢幕寬度
        螢幕高度 := SysGet(17)  ; 螢幕高度
        視窗X := (螢幕寬度 - 視窗寬度) / 2
        視窗Y := (螢幕高度 - 視窗高度) / 2
        
        ; 顯示視窗
        圖片視窗.Show("x" . 視窗X . " y" . 視窗Y)
        
        ShowToolTip("📷 背包座標設定圖例已開啟 (按 Esc 關閉)", 2000, 1)
    } catch Error as err {
        ShowToolTip("❌ 無法開啟圖片: " . err.message, 3000, 1)
    }
}

; 顯示場景偵測設定圖片指引
顯示場景偵測設定圖片() {
    try {
        if (!FileExist("image/偵測場景變化設置.png")) {
            ShowToolTip("❌ 找不到場景偵測設置圖片", 3000, 1)
            return
        }
        
        ; 創建圖片顯示視窗
        圖片視窗 := Gui("+Resize", "場景偵測設置圖例")
        圖片視窗.BackColor := "White"
        圖片視窗.Add("Text", "x20 y10 w400 h25 Center", "📷 場景偵測點設置參考圖例").SetFont("s12 Bold")
        圖片視窗.Add("Text", "x20 y40 w400 h25 Center", "請參考下圖設置場景變化偵測點").SetFont("s10")
        
        ; 添加圖片控件
        圖片控件 := 圖片視窗.Add("Picture", "x20 y70", "image/偵測場景變化設置.png")
        
        ; 獲取圖片尺寸以調整視窗大小
        圖片寬度 := 400  ; 預設寬度
        圖片高度 := 300  ; 預設高度
        
        ; 調整視窗大小
        視窗寬度 := 圖片寬度 + 40
        視窗高度 := 圖片高度 + 180  ; 增加高度給按鈕留空間
        
        圖片視窗.Move(, , 視窗寬度, 視窗高度)
        
        ; 添加關閉按鈕，放在圖片下方而非覆蓋在圖片上
        關閉按鈕 := 圖片視窗.Add("Button", "x" . (視窗寬度/2 - 60) . " y" . (圖片高度 + 90) . " w120 h35", "關閉 (Esc)")
        關閉按鈕.OnEvent("Click", (*) => 圖片視窗.Destroy())
        關閉按鈕.SetFont("s10 Bold")
        
        ; 加入Esc鍵支援
        圖片視窗.OnEvent("Escape", (*) => 圖片視窗.Destroy())
        圖片視窗.OnEvent("Close", (*) => 圖片視窗.Destroy())
        
        ; 將視窗顯示在螢幕中央
        螢幕寬度 := SysGet(16)  ; 螢幕寬度
        螢幕高度 := SysGet(17)  ; 螢幕高度
        視窗X := (螢幕寬度 - 視窗寬度) / 2
        視窗Y := (螢幕高度 - 視窗高度) / 2
        
        ; 顯示視窗
        圖片視窗.Show("x" . 視窗X . " y" . 視窗Y)
        
        ShowToolTip("📷 場景偵測設置圖例已開啟 (按 Esc 關閉)", 2000, 1)
    } catch Error as err {
        ShowToolTip("❌ 無法開啟圖片: " . err.message, 3000, 1)
    }
}

; 顯示對話框設定圖片指引
顯示對話框設定圖片() {
    try {
        if (!FileExist("image/對話框設置.png")) {
            ShowToolTip("❌ 找不到對話框設置圖片", 3000, 1)
            return
        }
        
        ; 創建圖片顯示視窗
        圖片視窗 := Gui("+Resize", "對話框設置圖例")
        圖片視窗.BackColor := "White"
        圖片視窗.Add("Text", "x20 y10 w400 h25 Center", "📷 對話框偵測點設置參考圖例").SetFont("s12 Bold")
        圖片視窗.Add("Text", "x20 y40 w400 h25 Center", "請參考下圖設置對話框1和對話框2的偵測點").SetFont("s10")
        
        ; 添加圖片控件
        圖片控件 := 圖片視窗.Add("Picture", "x20 y70", "image/對話框設置.png")
        
        ; 獲取圖片尺寸以調整視窗大小
        圖片寬度 := 400  ; 預設寬度
        圖片高度 := 300  ; 預設高度
        
        ; 調整視窗大小
        視窗寬度 := 圖片寬度 + 40
        視窗高度 := 圖片高度 + 180  ; 增加高度給按鈕留空間
        
        圖片視窗.Move(, , 視窗寬度, 視窗高度)
        
        ; 添加關閉按鈕，放在圖片下方而非覆蓋在圖片上
        關閉按鈕 := 圖片視窗.Add("Button", "x" . (視窗寬度/2 - 60) . " y" . (圖片高度 + 90) . " w120 h35", "關閉 (Esc)")
        關閉按鈕.OnEvent("Click", (*) => 圖片視窗.Destroy())
        關閉按鈕.SetFont("s10 Bold")
        
        ; 加入Esc鍵支援
        圖片視窗.OnEvent("Escape", (*) => 圖片視窗.Destroy())
        圖片視窗.OnEvent("Close", (*) => 圖片視窗.Destroy())
        
        ; 將視窗顯示在螢幕中央
        螢幕寬度 := SysGet(16)  ; 螢幕寬度
        螢幕高度 := SysGet(17)  ; 螢幕高度
        視窗X := (螢幕寬度 - 視窗寬度) / 2
        視窗Y := (螢幕高度 - 視窗高度) / 2
        
        ; 顯示視窗
        圖片視窗.Show("x" . 視窗X . " y" . 視窗Y)
        
        ShowToolTip("📷 對話框設置圖例已開啟 (按 Esc 關閉)", 2000, 1)
    } catch Error as err {
        ShowToolTip("❌ 無法開啟圖片: " . err.message, 3000, 1)
    }
}

