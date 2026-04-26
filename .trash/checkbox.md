<%*
// 1. 获取编辑器实例
const { editor } = app.workspace.activeEditor || {};
if (!editor) {
    new Notice("未发现活跃的编辑器");
    return;
}

// 2. 获取当前行
const lineNum = editor.getCursor().line;
const lineText = editor.getLine(lineNum);

// 3. 正则捕获：[1]缩进和横杠 [2]当前符号 [3]右括号和空格 [4]任务正文
const taskRegex = /^(\s*-\s\[)(.)(\]\s*)(.*)/;
const match = lineText.match(taskRegex);

if (!match) {
    new Notice("光标所在行不是有效的任务格式");
    return;
}

// 4. 定义 Minimal 主题全状态列表
// label 为空表示不需要在文本中插入额外的语义词（如 star, fire 等图标通常不需要文字）
const options = [
    { display: "[ ] To-do", s: " ", t: "" },
    { display: "[/] Incomplete", s: "/", t: "incomplete" },
    { display: "[x] Done", s: "x", t: "" },
    { display: "[-] Canceled", s: "-", t: "canceled" },
    { display: "[>] Forwarded/Pending", s: ">", t: "forwarded" },
    { display: "[<] Scheduling", s: "<", t: "scheduling" },
    { display: "[?] Question", s: "?", t: "question" },
    { display: "[!] Important", s: "!", t: "important" },
    { display: "[*] Star", s: "*", t: "" },
    { display: "[\"] Quote", s: "\"", t: "" },
    { display: "[l] Location", s: "l", t: "" },
    { display: "[b] Bookmark", s: "b", t: "" },
    { display: "[i] Information", s: "i", t: "" },
    { display: "[S] Savings", s: "S", t: "" },
    { display: "[I] Idea", s: "I", t: "idea" },
    { display: "[p] Pros", s: "p", t: "pros" },
    { display: "[c] Cons", s: "c", t: "cons" },
    { display: "[f] Fire", s: "f", t: "" },
    { display: "[k] Key", s: "k", t: "" },
    { display: "[w] Win", s: "w", t: "" },
    { display: "[u] Up", s: "u", t: "" },
    { display: "[d] Down", s: "d", t: "" }
];

// 5. 弹出选择器
const selected = await tp.system.suggester((opt) => opt.display, options);

if (selected) {
    let content = match[4].trim();
    
    // 鲁棒性优化：清理正文中可能存在的旧状态词
    // 遍历所有选项的 label，如果正文开头匹配到了任何一个 label，就将其剔除
    options.forEach(opt => {
        if (opt.t && content.toLowerCase().startsWith(opt.t)) {
            // 使用正则确保只匹配开头的独立单词
            const cleanRegex = new RegExp(`^${opt.t}\\s*`, 'i');
            content = content.replace(cleanRegex, "");
        }
    });

    // 6. 拼接新行
    // 如果有 label 则添加，否则只保留正文
    const statusWord = selected.t ? `${selected.t} ` : "";
    const newLine = `${match[1]}${selected.s}${match[3]}${statusWord}${content}`;
    
    editor.setLine(lineNum, newLine);
}
%>
