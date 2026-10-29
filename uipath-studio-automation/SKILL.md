---
name: uipath-studio-automation
description: Automate UiPath Studio on Windows through computer-use plus hand-edited XAML. Use when creating, editing, validating, running, or packaging UiPath workflow projects (RPA 财务机器人作业/考试, UiPath Studio 23.10, VB, Windows target, 含经典 Excel 活动). Do not use for web UI automation outside UiPath.
---

# UiPath Studio 自动化实操经验

环境基线：UiPath Studio 23.10.4（Academic Alliance，简体中文界面），工程 targetFramework=Windows、expressionLanguage=VisualBasic，依赖 UiPath.System.Activities 23.10.5、UiPath.Excel.Activities 2.22.3。

## 一、computer-use 调用模式

- 服务器名固定为 `ide_mcp.config.ext.computer-use`，在 Exec 里先定义：
  `async function cu(t,a){ return await tools.run_mcp({server_name:"ide_mcp.config.ext.computer-use",tool_name:t,args:a}); }`
- 流程：`list_apps` 拿 pid → `get_app_state`（观察）→ `click/type_text/press_key/set_value/perform_action`（操作）。
- 观察默认加 `disableScreenshot:true`；需要全新树时再加 `disableDiff:true`；深层树用 `max_depths:30+`。
- 报 `Action path changed / Action root could not be refreshed`：每次点击前重新取一次快照再操作。
- 报 `No window found for pid` / `pid is not running`：窗口或进程已重建。重新 `list_apps` 找新 pid。
- `type_text` 只能可靠输入 ASCII。中文输入无效；需要中文时用 `set_value` 或直接写文件。
- **键盘快捷键不可靠的根源是焦点**：焦点常在别的窗口（如 Trae）。最可靠做法：`press_key` 显式带 `element_id`（目标窗口/文档元素的 id），例如对 Main 文档窗口元素发 F5，一次成功。不要依赖 set_focus + 裸 press_key。
- 注意屏幕上可能出现 tooltip 悬浮窗口（"调试当前文件 (F6)"），它会污染快照、干扰点击，先按 Escape 或点击主窗口其他位置再操作。
- UiPath Studio 的设计器/属性面板在子进程 `UiPath.Studio.Project.exe` 里，但所有操作都对主进程 `UiPath.Studio.exe` 的 pid 下发。

## 二、在 Studio 里插入活动（备选方案，优先直接写 XAML）

1. 点击设计器里的"添加活动 (Ctrl + Shift + T)"按钮打开搜索框。
2. `type_text` 输入**英文活动名**（不带 element_id，靠焦点），例如 `InputDialog`、`While`、`Assign`、`Message Box`。
3. `press_key` Enter 插入。

## 三、直接编写 Main.xaml（推荐主路径）

最稳妥的流程：先用 Studio UI 新建空白工程（或复用已有合法工程），拿到合法 project.json 和头部骨架，再用编辑器整体重写 Main.xaml 内容。

- 文件编码 UTF-8 无 BOM，无 XML 声明，首字符必须是 `<Activity`。
- 保留 Studio 生成的整个头部：`Activity` 根属性、`TextExpression.NamespacesForImplementation`、`TextExpression.ReferencesForImplementation`（含 `xmlns:ui="http://schemas.uipath.com/workflow/activities"`），只替换 `<Sequence>` 内部。
- 变量写在 `<Sequence.Variables>`：`<Variable x:TypeArguments="x:Int32" Default="1" Name="n" />`。
- **InArgument 与 Activity<bool> 都可用属性表达式写法**：`Condition="[n &lt;= 100]"`（If、InterruptibleWhile、InterruptibleDoWhile 均验证可绑定；`<` 转义为 `&lt;`）。
- **OutArgument 必须用元素写法**，写成属性会报"String 不可分配给成员 Result 的类型 OutArgument"：

```xml
<ui:InputDialog IsPassword="False" Label="[&quot;请输入现值 P：&quot;]" Options="{x:Null}" OptionsString="{x:Null}" Title="[&quot;终值计算&quot;]" DisplayName="输入对话框 - 现值">
  <ui:InputDialog.Result>
    <OutArgument x:TypeArguments="x:String">[strP]</OutArgument>
  </ui:InputDialog.Result>
</ui:InputDialog>
```

- Assign：`<Assign.To><OutArgument x:TypeArguments="x:Int32">[n]</OutArgument></Assign.To>` + `<Assign.Value><InArgument x:TypeArguments="x:Int32">[n + 1]</InArgument></Assign.Value>`。
- **先条件循环（While）**：`<ui:InterruptibleWhile Condition="[n &lt;= 100]" CurrentIndex="{x:Null}"><ui:InterruptibleWhile.Body><Sequence>…</Sequence></ui:InterruptibleWhile.Body></ui:InterruptibleWhile>`（已验证）。
- **后条件循环（Do While）**：用 `<ui:InterruptibleDoWhile Condition="[n &lt;= 100]" CurrentIndex="{x:Null}"><ui:InterruptibleDoWhile.Body><Sequence>…</Sequence></ui:InterruptibleDoWhile.Body></ui:InterruptibleDoWhile>`。**不要**写原生无前缀 `<DoWhile>`——Studio 加载时会把它替换成 InterruptibleDoWhile，丢掉条件和正文内容，报"此活动丢失或无法加载"。
- If：`<If Condition="[n Mod 2 = 1]"><If.Then><ui:LogMessage …/></If.Then></If>`（无前缀，默认命名空间）。
- 日志消息：`<ui:LogMessage Level="Info" Message="[n.ToString()]" />`。
- 消息框：`<ui:MessageBox Text="[&quot;结果 = &quot; + Math.Round(F, 2).ToString()]" />`。
- `InputDialog` 的 `Options="{x:Null}"` 可正常运行：单个"确定"按钮 + 文本框。
- **没把握的活动写法，先查 Studio 自带代码片段**：`C:\Users\<user>\AppData\Local\Programs\UiPath\Studio\Snippets\`（按 Legacy/Portable/Windows × CSharp/VBasic 分类，如 Loops\Repeat With Counter.xaml）。
- 也可反射查活动属性类型（见第八节）。

### DataTable 变量声明（Windows vs Legacy 命名空间不同！）

- **Windows 工程**：`xmlns:sd="clr-namespace:System.Data;assembly=System.Data.Common"`（net6 里 DataTable 在 System.Data.Common.dll）。
- **Legacy 工程**：`xmlns:sd="clr-namespace:System.Data;assembly=System.Data"`。
- 声明：`<Variable x:TypeArguments="sd:DataTable" Name="data" />`。
- 依据：Studio 自带片段 `Snippets\Windows\SnippetsVBasic\Samples\Advanced\Filter DataTable Using LINQ.xaml` 第一行。

## 四、经典 Excel 活动序列化（UiPath.Excel.Activities 2.22.3，已逐一反射验证属性类型）

完整骨架（读取 → 筛选列 → 写入 → 建表 → 建透视表，全部包在 Excel 应用程序范围内）：

```xml
<ui:ExcelApplicationScope AutoSave="True" DisplayName="Excel 应用程序范围" WorkbookPath="[&quot;数据.xlsx&quot;]">
  <ui:ExcelApplicationScope.Body>
    <ActivityAction x:TypeArguments="ui:WorkbookApplication">
      <ActivityAction.Argument>
        <DelegateInArgument x:TypeArguments="ui:WorkbookApplication" Name="ExcelWorkbookScope" />
      </ActivityAction.Argument>
      <Sequence DisplayName="执行">
        <Sequence.Variables>
          <Variable x:TypeArguments="sd:DataTable" Name="data" />
          <Variable x:TypeArguments="sd:DataTable" Name="data_1" />
        </Sequence.Variables>
        <!-- 5 个活动依次放这里 -->
      </Sequence>
    </ActivityAction>
  </ui:ExcelApplicationScope.Body>
</ui:ExcelApplicationScope>
```

- **ExcelApplicationScope**：`WorkbookPath`(InArgument str，可用相对路径)、`AutoSave`/`Visible`(bool)。Body 类型是 `ActivityAction<ui:WorkbookApplication>`（写成 `ui:Workbook` 会导致整个子树变成 UnresolvedActivity，报"类型 ActivityAction(Workbook) 不可分配给成员 Body"），**必须**按上面委托写法包一层；`DelegateInArgument` 的 Name 固定写 `ExcelWorkbookScope`。
- **ExcelReadRange**：`SheetName`(InArgument str)、`Range`(InArgument str，省略或 `{x:Null}` = 整表)、`AddHeaders`(bool)、`DataTable`(**OutArgument\<DataTable\>**，用元素写法)：

```xml
<ui:ExcelReadRange AddHeaders="True" SheetName="[&quot;Sheet1&quot;]" DisplayName="读取范围">
  <ui:ExcelReadRange.DataTable>
    <OutArgument x:TypeArguments="sd:DataTable">[data]</OutArgument>
  </ui:ExcelReadRange.DataTable>
</ui:ExcelReadRange>
```

- **FilterDataTable**（UiPath.Core.Activities，同样映射 ui 前缀）：`DataTable`(InArgument\<DataTable\>，属性写法 `DataTable="[data]"`)、`SelectColumnsMode`/`FilterRowsMode`(InArgument 枚举，写 `[UiPath.Core.Activities.SelectMode.Keep]`)、`SelectColumns`(**List\<InArgument\>**，元素写法)、`OutputDataTable`(OutArgument\<DataTable\>，元素写法)：

```xml
<ui:FilterDataTable DataTable="[data]" DisplayName="筛选数据表" SelectColumnsMode="[UiPath.Core.Activities.SelectMode.Keep]">
  <ui:FilterDataTable.SelectColumns>
    <scg:List x:TypeArguments="InArgument" Capacity="6">
      <InArgument x:TypeArguments="x:String">[&quot;一级部门&quot;]</InArgument>
      <InArgument x:TypeArguments="x:String">[&quot;基本薪资&quot;]</InArgument>
    </scg:List>
  </ui:FilterDataTable.SelectColumns>
  <ui:FilterDataTable.OutputDataTable>
    <OutArgument x:TypeArguments="sd:DataTable">[data_1]</OutArgument>
  </ui:FilterDataTable.OutputDataTable>
</ui:FilterDataTable>
```

- **ExcelWriteRange**：`SheetName`、`StartingCell`(InArgument str)、`DataTable`(**InArgument**\<DataTable\>，属性写法 `DataTable="[data_1]"`)、`AddHeaders`。Sheet 不存在会自动新建。
- **ExcelCreateTable**：`Range`、`TableName`、`SheetName`（均 InArgument str）。
- **ExcelCreatePivotTable**：`SourceTableName`、`Range`（透视表左上角）、`TableName`、`SheetName`（均 InArgument str）。**XAML 里没有字段布局属性**——透视表行/列/值字段只能在设计器向导里配置，手写 XAML 只能创建空透视表骨架，字段需运行后在 Excel 里拖，或接受空布局。
- 列重命名等 DataTable 操作可用 Assign：`OutArgument x:TypeArguments="x:String">[data_1.Columns(&quot;旧名&quot;).ColumnName]` → `InArgument>[&quot;新名&quot;]`。
- **工程自包含**：把源数据 xlsx 复制进工程目录，WorkbookPath 写相对路径，zip 解压即可运行。
- ReferencesForImplementation 需加 `<AssemblyReference>UiPath.Excel.Activities</AssemblyReference>`。

## 四·二、邮件活动（UiPath.Mail.Activities 1.21.1，来自参考答案 Main.xaml 实测）

命名空间与引用（Windows 工程）：

```xml
xmlns:snm="clr-namespace:System.Net.Mail;assembly=System.Net.Mail"
<!-- NamespacesForImplementation 追加 -->
<x:String>System.Security</x:String>
<x:String>UiPath.Mail</x:String>
<x:String>UiPath.Mail.POP3.Activities</x:String>
<x:String>UiPath.Mail.Activities</x:String>
<!-- ReferencesForImplementation 追加 -->
<AssemblyReference>UiPath.Mail.Activities</AssemblyReference>
<AssemblyReference>UiPath.Mail</AssemblyReference>
```

变量：`List<MailMessage>` 写作 `<Variable x:TypeArguments="scg:List(snm:MailMessage)" Name="mail" />`（放在序列的 Sequence.Variables 里，范围=序列）。

```xml
<ui:GetPOP3MailMessages SecurePassword="{x:Null}" TimeoutMS="{x:Null}" UseOAuth="{x:Null}"
    DeleteMessages="True" DisplayName="获取 POP3 邮件消息" Email="xxx@163.com" EnableSSL="False"
    IdRef="GetPOP3MailMessages_1" IgnoreCRL="False" Messages="[mail]" Password="授权码"
    Port="995" SecureConnection="Auto" Server="pop.163.com" Top="30" />
```

- **GetPOP3MailMessages**：`Server`/`Email`/`Password`(163 用授权码)/`Port`/`Messages`(OutArgument，属性写法 `Messages="[mail]"`)/`Top`(取几封，题里 30)/`DeleteMessages`(勾选=取完删除)/`EnableSSL`/`SecureConnection="Auto"`/`IgnoreCRL`/`SecurePassword`/`TimeoutMS`/`UseOAuth`（后 4 个固定 `{x:Null}`）。
- **ForEach 遍历 MailMessage**：`x:TypeArguments="snm:MailMessage"`、`Values="[mail]"`、`CurrentIndex="{x:Null}"`，Body 里 `ActivityAction x:TypeArguments="snm:MailMessage"` + `DelegateInArgument x:TypeArguments="snm:MailMessage" Name="currentItem"`。
- **If 条件**：`[currentItem.Subject.Contains("采购明细表") or currentItem.Subject.Contains("领料明细表")]`（用 `QUOT` XML 中转义引号）。
- **SaveMailAttachments**：`Message="[currentItem]"`、`FolderPath="{x:Null}"`（留空=保存到当前运行目录/工程目录）、`OverwriteExisting="False"`、`ExcludeInlineAttachments="False"`、`Attachments="{x:Null}"`。

流程框架：`序列 → 获取POP3邮件消息 → 遍历循环(mail) → 序列(正文) → IF条件 → Then → 保存附件`。
前置人工步骤（题目要求 1）：先用采购明细表 / 领料明细表各发一封主题含对应名称的邮件到同一邮箱，机器人才能取到。

## 五、重载与校验

- Studio 不会自动重载外部改过的文件。重载：对 Main 文档窗口元素 `press_key` Ctrl+F4 → 若弹保存对话框选**"否"**（避免内存里的旧/坏状态回写磁盘）→ 点击"打开主工作流"超链接。
- "此活动丢失或无法加载" + "该文档有未解决的活动"横幅 = 有活动类型解析失败，此时无法保存，但错误列表可能仍显示 0 错误——以设计器里的红色错误图标和该横幅为准。
- 错误列表可能残留**旧版本的报错**（如"条件为必填项"残留误报）。以重新加载 + 重新校验为准（干净状态：错误 0 / 警告 0）。
- 外部重写文件后设计器按钮可能提示"已禁用，因为该文件是只读文件"。不影响按磁盘文件运行；要恢复可编辑可重启 Studio。

## 六、运行与结果验证

- **最可靠的运行触发**：`press_key` 带 `element_id`（Main 文档窗口 id）发 F5。功能区 split-button（调试文件）点击不稳定（toggle/下拉/tooltip 干扰）。
- **运行（F5/调试）前 Studio 会自动保存**，用内存序列化覆盖磁盘文件——外部刚改完文件时，务必先重载确认设计器状态正确再运行，否则坏状态会被写回磁盘。
- 每次弹出 InputDialog/MessageBox 都会启动**新的 WorkerProcess.exe（pid 每次变）**，每步之间重新 `list_apps`；填输入框用 `set_value`，再 click"确定"。
- 验证日志类作业：看输出面板"信息 N"计数（= 业务日志数 + 2 条系统执行日志），list-item 文本直接含日志内容。
- Excel 类作业：运行时 Excel 会可见打开（Visible 默认 True），留 30-60 秒执行时间；验证输出工作簿里新增的 sheet / 表对象 / 透视表 sheet。需本机装有 Microsoft Excel（Interop）。
- 已验证基准用例：
  - 复利终值：P=100、n=3、i=0.05 → 消息框 `复利终值 F = 115.76`
  - 奇数输出：n<=100 内奇数 → 信息 52 条（50 个奇数 + 2 系统日志）
  - 合计数：1到100 sum → 日志 `1到100的合计数 = 5050`

## 七、打包交付

- 完整工程 = Main.xaml + project.json（.settings/.project/.local 等由 Studio 自动生成，可一并打包；含数据文件的工程把 xlsx 一起打进 zip）。
- 压缩：`Compress-Archive -Path <工程文件夹> -DestinationPath <目标.zip> -Force`，再用 `System.IO.Compression.ZipFile` 列条目验证。
- Studio 打开工程时会锁定 `.local` 下 dll，此时删文件夹会 Access denied——先在 Studio 里关闭该工程再删（zip 读取不受影响）。

## 八、启动 Studio 与文件操作的环境坑

- **打开工程**：`Start-Process '<Studio>\UiPath.Studio.exe' -ArgumentList '"<project.json路径>"'`。第一次调用可能**静默失败**（进程根本没起来），必须 `-PassThru` 拿进程对象 + `Start-Sleep` 后查 `Get-Process *Studio*` 确认；失败就原样重发一次。
- **沙箱限制**：Trae 的 Shell 沙箱对桌面等目录写入会报 `Access denied / Not allow operate files`（如 Copy-Item 到桌面文件夹失败）。对策：**写文本文件一律用 Trae 的 Write 工具直接写绝对路径**（不受沙箱限）；复制二进制文件（xlsx）需用户先放到可写区或关闭沙箱执行。
- **探查 xlsx 结构**（无需 Excel/Python）：xlsx 是 zip，PowerShell 解压后读：
  - `xl\workbook.xml` → sheet 名称
  - `xl\worksheets\sheet1.xml` → `dimension.ref`（如 A1:K72）
  - `xl\sharedStrings.xml` → 全部字符串（表头、文本单元格）

  ```powershell
  Add-Type -AssemblyName System.IO.Compression.FileSystem
  [System.IO.Compression.ZipFile]::ExtractToDirectory($xlsx, $tmp)
  ```

- **反射验证活动属性类型**（没把握的活动先查再写）：
  - PS5.1 里 `ReflectionOnlyLoadFrom` 加载 `~\.nuget\packages\<包>\*\lib\net461\*.dll`（net6 程序集在 PS5.1 反射不可靠，必须用 net461 legacy 版）。
  - 需先 ReflectionOnlyLoad System.Activities / System.Xaml / mscorlib，并注册 `[AppDomain]::CurrentDomain.add_ReflectionOnlyAssemblyResolve({...})` 在同目录探测依赖，否则 GetType 失败。
  - `GetTypes()` 抛 ReflectionTypeLoadException 时用 `$_.Exception.Types | Where-Object {$_ -ne $null}` 容错。
  - 经典 Excel 活动在 `UiPath.Excel.Activities.dll`（不是 UiPath.Excel.dll）；FilterDataTable 在 `UiPath.System.Activities.dll`（UiPath.Core.Activities 命名空间）。
- PowerShell 注意：`foreach{} | Format-Table` 空管道元素会语法错误，先收集到数组再格式化。

## 九、排错速查

| 现象 | 原因与对策 |
|------|-----------|
| "此活动丢失或无法加载" | 活动写法不对（如原生 `<DoWhile>`）；改用 ui:Interruptible* 形式重载 |
| 错误列表"条件为必填项"但设计器条件有值 | 残留误报；重新加载+校验确认 |
| Result 类型 OutArgument 报错 | OutArgument 改元素写法 |
| DataTable 变量解析失败 | Windows 工程 sd 命名空间必须是 assembly=System.Data.Common |
| ExcelApplicationScope 报 Body 类型错 | Body 是 ActivityAction\<ui:WorkbookApplication\>，写 ui:Workbook 会整棵子树失效 |
| 创建表格报 0x8FE30C19（ListObjects.Add） | 工作簿里已有同名表对象；每次运行前恢复干净的数据文件（或加"复制文件"步骤覆盖） |
| 课评平台运行后表头变成"列1/列2…" | 平台上只解压源码、不同步 xlsx；在 Excel 范围前加"复制文件"从固定绝对路径复制数据到当前目录 |
| 搜索框输中文没反应 | type_text 不支持中文；改英文活动名 |
| F5/F6 没反应 | 键盘焦点在别的窗口；press_key 带 element_id 直发目标窗口 |
| split-button 点击无效 | tooltip/下拉干扰；Escape 后改用键盘快捷键 |
| 点完"确定"后工具报 pid not running | WorkerProcess 已退出换新 pid；重新 list_apps |
| 运行后手写的 XAML 被改写 | 运行触发自动保存；先确保设计器状态正确再运行 |
| 文件权限正常却提示只读 | Studio 会话状态；杀残留 Studio.Project 进程或重启 Studio |
| Start-Process 后 Studio 没起来 | 静默失败常见；加 -PassThru 确认，失败重发 |
| Shell 写桌面 Access denied | 沙箱限制；改用 Write 工具写文件 |
| 反射加载程序集依赖失败 | 预加载 GAC 程序集 + ReflectionOnlyAssemblyResolve 探测包目录 |

## 附：换设备后如何安装这个 skill

把这个 md 文件放到新设备的 `~/.trae-cn/skills/uipath-studio-automation/SKILL.md`（即新建 `uipath-studio-automation` 文件夹，文件重命名为 `SKILL.md`），重启 Trae CN 即可被自动加载。
