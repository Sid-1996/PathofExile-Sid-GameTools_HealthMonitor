; 滑鼠自動連點工具 (AHK v2)
; 按住 CTRL+左鍵 進行50ms間隔自動點擊
; 自動監測主程式進程，當主程式退出時自動關閉
; 支援編譯前後的進程名稱匹配

#SingleInstance Force
Persistent()

; 設定變數
global clickInterval := 50  ; 50ms點擊間隔
global isClicking := false
global parentProcessName := ""  ; 父進程名稱
global monitorInterval := 2000  ; 每2秒檢查一次進程

; 啟動時獲取父進程名稱
GetParentProcessName() {
    global parentProcessName
    
    ; 檢查命令列參數
    if (A_Args.Length > 0) {
        parentProcessName := A_Args[1]
        TrayTip("滑鼠連點工具", "從參數獲取進程名稱: " . parentProcessName, 16)
        return
    }
    
    ; 如果沒有參數，延遲偵測以確保主程式已完全啟動
    ; 優先偵測編譯後的exe名稱
    if (ProcessExist("GameTools_HealthMonitor.exe")) {
        parentProcessName := "GameTools_HealthMonitor.exe"
        TrayTip("滑鼠連點工具", "偵測到編譯版本: " . parentProcessName, 16)
    }
    ; 其次偵測開發環境的python進程 - 檢測多種可能的Python版本
    else if (ProcessExist("python3.10.exe")) {
        parentProcessName := "python3.10.exe"
        TrayTip("滑鼠連點工具", "偵測到Python 3.10: " . parentProcessName, 16)
    }
    else if (ProcessExist("python3.11.exe")) {
        parentProcessName := "python3.11.exe"
        TrayTip("滑鼠連點工具", "偵測到Python 3.11: " . parentProcessName, 16)
    }
    else if (ProcessExist("python3.12.exe")) {
        parentProcessName := "python3.12.exe"
        TrayTip("滑鼠連點工具", "偵測到Python 3.12: " . parentProcessName, 16)
    }
    else if (ProcessExist("python.exe")) {
        parentProcessName := "python.exe"
        TrayTip("滑鼠連點工具", "偵測到Python: " . parentProcessName, 16)
    }
    else if (ProcessExist("pythonw.exe")) {
        parentProcessName := "pythonw.exe"
        TrayTip("滑鼠連點工具", "偵測到Pythonw: " . parentProcessName, 16)
    }
    else {
        ; 如果都找不到，設置預設值但延遲檢查
        parentProcessName := "GameTools_HealthMonitor.exe"
        TrayTip("滑鼠連點工具", "使用預設值: " . parentProcessName, 16)
    }
}

; 初始化
GetParentProcessName()

; 延遲啟動進程監測，給主程式足夠時間啟動
if (parentProcessName != "") {
    ; 延遲5秒再開始監測，確保主程式完全啟動
    SetTimer(() => SetTimer(CheckParentProcess, monitorInterval), 5000)
    TrayTip("滑鼠連點工具", "已啟動，將於5秒後開始監測進程: " . parentProcessName, 16)
} else {
    TrayTip("滑鼠連點工具", "警告：無法確定父進程名稱", 16)
}

; 檢查父進程是否仍然存在
CheckParentProcess() {
    global parentProcessName
    
    if (parentProcessName = "") {
        return  ; 如果沒有有效的父進程名稱，不進行檢查
    }
    
    ; 檢查指定名稱的進程是否仍然存在
    if (!ProcessExist(parentProcessName)) {
        ; 如果父進程不存在，自動關閉
        TrayTip("滑鼠連點工具", "父進程(" . parentProcessName . ")已退出，自動關閉連點工具", 16)
        SetTimer(CheckParentProcess, 0)  ; 停止監測
        Sleep(500)  ; 等待0.5秒
        ExitApp()
    } else {
        ; 調試信息：確認進程存在
        ; TrayTip("滑鼠連點工具", "監測中：進程(" . parentProcessName . ")運行正常", 16)
    }
}

; 監聽CTRL+左鍵組合
~*LButton:: {
    global isClicking, clickInterval
    ; 檢查CTRL是否按下
    if (GetKeyState("Ctrl", "P")) {
        if (!isClicking) {
            isClicking := true
            ; TrayTip("滑鼠連點工具", "自動點擊已啟動", 16)
            SetTimer(AutoClick, clickInterval)
        }
    }
}

; 左鍵釋放時停止連點
~*LButton Up:: {
    global isClicking
    if (isClicking) {
        isClicking := false
        ; TrayTip("滑鼠連點工具", "自動點擊已停止", 16)
        SetTimer(AutoClick, 0)
    }
}

; CTRL鍵釋放時也停止連點
~*Ctrl Up:: {
    global isClicking
    if (isClicking) {
        isClicking := false
        ; TrayTip("滑鼠連點工具", "自動點擊已停止", 16)
        SetTimer(AutoClick, 0)
    }
}

; 自動點擊函數
AutoClick() {
    global isClicking
    ; 檢查是否仍然同時按住CTRL+左鍵
    if (isClicking && GetKeyState("Ctrl", "P") && GetKeyState("LButton", "P")) {
        Click()
    } else {
        ; 如果任何一個按鍵釋放，停止點擊
        isClicking := false
        SetTimer(AutoClick, 0)
        ; TrayTip("滑鼠連點工具", "自動點擊已停止", 16)
    }
}

; 手動退出熱鍵 (Ctrl+Alt+Q) - 保留作為備用
^!q:: {
    ; TrayTip("滑鼠連點工具", "手動退出", 16)
    ExitApp()
}