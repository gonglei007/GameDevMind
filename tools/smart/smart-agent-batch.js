#!/usr/bin/env node
/**
 * Smart API 批量执行 Agent 脚本
 * 通过 Smart API 批量执行 agent，提示词中可以引用文件
 */

const fs = require('fs');
const path = require('path');
const https = require('https');
const http = require('http');

// 配置
const CONFIG = {
  // Smart API 配置
  apiUrl: process.env.SMART_API_URL || 'https://api.smart.sh/v1/chat/completions',
  apiKey: process.env.SMART_API_KEY || '',
  
  // 请求配置
  timeout: 60000, // 60秒超时
  maxRetries: 3, // 最大重试次数
  retryDelay: 1000, // 重试延迟（毫秒）
  
  // 文件路径
  configFile: path.join(__dirname, 'smart-agent-config.json'),
  exampleConfigFile: path.join(__dirname, 'smart-agent-config.example.json'),
  outputDir: path.join(__dirname, 'smart-agent-output'),
};

// 颜色输出
const colors = {
  reset: '\x1b[0m',
  red: '\x1b[31m',
  green: '\x1b[32m',
  yellow: '\x1b[33m',
  blue: '\x1b[34m',
  cyan: '\x1b[36m',
};

function log(message, color = 'reset') {
  console.log(`${colors[color]}${message}${colors.reset}`);
}

/**
 * 读取配置文件
 */
function loadConfig() {
  if (!fs.existsSync(CONFIG.configFile)) {
    log(`配置文件不存在: ${CONFIG.configFile}`, 'yellow');
    
    // 检查是否有示例配置文件
    if (fs.existsSync(CONFIG.exampleConfigFile)) {
      log(`发现示例配置文件: ${CONFIG.exampleConfigFile}`, 'yellow');
      log('请复制示例配置文件并设置 API Key:', 'yellow');
      log(`  cp ${path.basename(CONFIG.exampleConfigFile)} ${path.basename(CONFIG.configFile)}`, 'cyan');
    } else {
      log('创建示例配置文件...', 'yellow');
      createExampleConfig();
    }
    process.exit(1);
  }
  
  try {
    const configContent = fs.readFileSync(CONFIG.configFile, 'utf-8');
    return JSON.parse(configContent);
  } catch (error) {
    log(`读取配置文件失败: ${error.message}`, 'red');
    process.exit(1);
  }
}

/**
 * 从 git 获取仓库 URL
 */
function getRepositoryFromGit() {
  try {
    const { execSync } = require('child_process');
    const projectRoot = path.resolve(__dirname, '../..');
    const remoteUrl = execSync('git config --get remote.origin.url', { 
      cwd: projectRoot,
      encoding: 'utf-8',
      stdio: ['ignore', 'pipe', 'ignore']
    }).trim();
    
    // 转换 SSH URL 为 HTTPS URL
    if (remoteUrl.startsWith('git@')) {
      const match = remoteUrl.match(/git@([^:]+):(.+)\.git/);
      if (match) {
        return `https://${match[1]}/${match[2]}`;
      }
    } else if (remoteUrl.startsWith('http')) {
      // 移除 .git 后缀（如果有）
      return remoteUrl.replace(/\.git$/, '');
    }
    
    return remoteUrl;
  } catch (error) {
    return null;
  }
}

/**
 * 创建示例配置文件
 */
function createExampleConfig() {
  const exampleConfig = {
    "apiKey": "",
    "apiUrl": "https://api.cursor.com/v0/agents",
    "model": "auto",
    "repository": "https://github.com/your-org/your-repo",
    "ref": "main",
    "maxWaitTime": 300000,
    "delayBetweenTasks": 2000,
    "tasks": [
      {
        "id": "task-1",
        "prompt": "基于 @INTRODUCTION.md 的定位、目标和 @xminds/1.基础能力/1.1.1.编程语言基础概念.md 的内容，来更新丰富 @mds/1.基础能力/1.1.1.编程语言基础概念.md 文件的内容。",
        "files": [
          "INTRODUCTION.md",
          "xminds/1.基础能力/1.1.1.编程语言基础概念.md",
          "mds/1.基础能力/1.1.1.编程语言基础概念.md"
        ],
        "outputFile": "output/task-1-result.md"
      }
    ]
  };
  
  fs.writeFileSync(CONFIG.exampleConfigFile, JSON.stringify(exampleConfig, null, 2), 'utf-8');
  log(`已创建示例配置文件: ${CONFIG.exampleConfigFile}`, 'green');
  log('请复制示例配置文件并设置 API Key 和 repository:', 'yellow');
  log(`  cp ${path.basename(CONFIG.exampleConfigFile)} ${path.basename(CONFIG.configFile)}`, 'cyan');
}

/**
 * 读取文件内容
 */
function readFileContent(filePath) {
  // 从 tools/smart/ 目录向上两级到项目根目录
  const projectRoot = path.resolve(__dirname, '../..');
  const fullPath = path.resolve(projectRoot, filePath);
  
  if (!fs.existsSync(fullPath)) {
    log(`文件不存在: ${filePath} (完整路径: ${fullPath})`, 'yellow');
    return null;
  }
  
  try {
    return fs.readFileSync(fullPath, 'utf-8');
  } catch (error) {
    log(`读取文件失败 ${filePath}: ${error.message}`, 'red');
    return null;
  }
}

/**
 * 构建包含文件引用的提示词
 */
function buildPromptWithFiles(basePrompt, files) {
  let prompt = basePrompt;
  
  if (files && files.length > 0) {
    const fileContents = [];
    
    for (const file of files) {
      const content = readFileContent(file);
      if (content) {
        fileContents.push(`## 文件: ${file}\n\n\`\`\`\n${content}\n\`\`\``);
      }
    }
    
    if (fileContents.length > 0) {
      prompt = `${basePrompt}\n\n## 参考文件内容:\n\n${fileContents.join('\n\n')}`;
    }
  }
  
  return prompt;
}

/**
 * 调用 Smart API (Cursor Cloud Agent API)
 */
async function callSmartAPI(config, prompt, retryCount = 0) {
  return new Promise((resolve, reject) => {
    // Cursor Cloud Agent API 需要 prompt 和 source 字段
    if (!config.repository) {
      reject(new Error('配置文件中缺少必需的 repository 字段。请设置 GitHub 仓库 URL。'));
      return;
    }

    const requestData = JSON.stringify({
      prompt: {
        text: prompt
      },
      source: {
        repository: config.repository,
        ref: config.ref || 'main'
      },
      ...(config.model && config.model !== 'auto' ? { model: config.model } : {})
    });
    
    const url = new URL(config.apiUrl || CONFIG.apiUrl);
    const apiKey = config.apiKey || CONFIG.apiKey;
    
    // Cursor API 使用 Basic Authentication
    const auth = Buffer.from(`${apiKey}:`).toString('base64');
    
    const options = {
      hostname: url.hostname,
      port: url.port || (url.protocol === 'https:' ? 443 : 80),
      path: url.pathname,
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Content-Length': Buffer.byteLength(requestData),
        'Authorization': `Basic ${auth}`,
      },
      timeout: CONFIG.timeout,
    };
    
    const client = url.protocol === 'https:' ? https : http;
    
    const req = client.request(options, (res) => {
      let data = '';
      
      res.on('data', (chunk) => {
        data += chunk;
      });
      
      res.on('end', () => {
        if (res.statusCode >= 200 && res.statusCode < 300) {
          try {
            const response = JSON.parse(data);
            resolve(response);
          } catch (error) {
            reject(new Error(`解析响应失败: ${error.message}`));
          }
        } else {
          // 如果失败且还有重试次数，进行重试
          if (retryCount < CONFIG.maxRetries) {
            log(`请求失败 (${res.statusCode})，${CONFIG.retryDelay}ms 后重试 (${retryCount + 1}/${CONFIG.maxRetries})...`, 'yellow');
            setTimeout(() => {
              callSmartAPI(config, prompt, retryCount + 1)
                .then(resolve)
                .catch(reject);
            }, CONFIG.retryDelay);
          } else {
            reject(new Error(`API 请求失败: ${res.statusCode} - ${data}`));
          }
        }
      });
    });
    
    req.on('error', (error) => {
      // 如果失败且还有重试次数，进行重试
      if (retryCount < CONFIG.maxRetries) {
        log(`请求错误: ${error.message}，${CONFIG.retryDelay}ms 后重试 (${retryCount + 1}/${CONFIG.maxRetries})...`, 'yellow');
        setTimeout(() => {
          callSmartAPI(config, prompt, retryCount + 1)
            .then(resolve)
            .catch(reject);
        }, CONFIG.retryDelay);
      } else {
        reject(error);
      }
    });
    
    req.on('timeout', () => {
      req.destroy();
      if (retryCount < CONFIG.maxRetries) {
        log(`请求超时，${CONFIG.retryDelay}ms 后重试 (${retryCount + 1}/${CONFIG.maxRetries})...`, 'yellow');
        setTimeout(() => {
          callSmartAPI(config, prompt, retryCount + 1)
            .then(resolve)
            .catch(reject);
        }, CONFIG.retryDelay);
      } else {
        reject(new Error('请求超时'));
      }
    });
    
    req.write(requestData);
    req.end();
  });
}

/**
 * 轮询 Agent 状态
 */
async function pollAgentStatus(config, agentId, maxWaitTime = 300000) {
  const startTime = Date.now();
  const pollInterval = 5000; // 5秒轮询一次
  
  return new Promise((resolve, reject) => {
    const checkStatus = async () => {
      try {
        const url = new URL(config.apiUrl || CONFIG.apiUrl);
        const apiKey = config.apiKey || CONFIG.apiKey;
        const auth = Buffer.from(`${apiKey}:`).toString('base64');
        
        const options = {
          hostname: url.hostname,
          port: url.port || (url.protocol === 'https:' ? 443 : 80),
          path: `${url.pathname}/${agentId}`,
          method: 'GET',
          headers: {
            'Authorization': `Basic ${auth}`,
          },
          timeout: CONFIG.timeout,
        };
        
        const client = url.protocol === 'https:' ? https : http;
        
        const req = client.request(options, (res) => {
          let data = '';
          res.on('data', (chunk) => { data += chunk; });
          res.on('end', () => {
            if (res.statusCode >= 200 && res.statusCode < 300) {
              try {
                const response = JSON.parse(data);
                const status = response.status;
                
                if (status === 'FINISHED' || status === 'FAILED' || status === 'STOPPED') {
                  resolve(response);
                } else if (Date.now() - startTime > maxWaitTime) {
                  reject(new Error(`Agent 超时: 等待时间超过 ${maxWaitTime / 1000} 秒`));
                } else {
                  log(`Agent 状态: ${status}, 继续等待...`, 'yellow');
                  setTimeout(checkStatus, pollInterval);
                }
              } catch (error) {
                reject(new Error(`解析状态响应失败: ${error.message}`));
              }
            } else {
              reject(new Error(`获取 Agent 状态失败: ${res.statusCode} - ${data}`));
            }
          });
        });
        
        req.on('error', reject);
        req.on('timeout', () => {
          req.destroy();
          reject(new Error('获取 Agent 状态超时'));
        });
        
        req.end();
      } catch (error) {
        reject(error);
      }
    };
    
    checkStatus();
  });
}

/**
 * 获取 Agent 对话内容
 */
async function getAgentConversation(config, agentId) {
  return new Promise((resolve, reject) => {
    const url = new URL(config.apiUrl || CONFIG.apiUrl);
    const apiKey = config.apiKey || CONFIG.apiKey;
    const auth = Buffer.from(`${apiKey}:`).toString('base64');
    
    const options = {
      hostname: url.hostname,
      port: url.port || (url.protocol === 'https:' ? 443 : 80),
      path: `${url.pathname}/${agentId}/conversation`,
      method: 'GET',
      headers: {
        'Authorization': `Basic ${auth}`,
      },
      timeout: CONFIG.timeout,
    };
    
    const client = url.protocol === 'https:' ? https : http;
    
    const req = client.request(options, (res) => {
      let data = '';
      res.on('data', (chunk) => { data += chunk; });
      res.on('end', () => {
        if (res.statusCode >= 200 && res.statusCode < 300) {
          try {
            const response = JSON.parse(data);
            resolve(response);
          } catch (error) {
            reject(new Error(`解析对话响应失败: ${error.message}`));
          }
        } else {
          reject(new Error(`获取对话失败: ${res.statusCode} - ${data}`));
        }
      });
    });
    
    req.on('error', reject);
    req.on('timeout', () => {
      req.destroy();
      reject(new Error('获取对话超时'));
    });
    
    req.end();
  });
}

/**
 * 处理单个任务
 */
async function processTask(config, task, index, total) {
  log(`\n[${index + 1}/${total}] 处理任务: ${task.id}`, 'cyan');
  
  // 构建包含文件引用的提示词
  const prompt = buildPromptWithFiles(task.prompt, task.files);
  
  if (task.files && task.files.length > 0) {
    log(`引用文件: ${task.files.join(', ')}`, 'blue');
  }
  
  try {
    // 调用 API 启动 Agent
    log('正在启动 Cursor Cloud Agent...', 'yellow');
    const launchResponse = await callSmartAPI(config, prompt);
    
    if (!launchResponse.id) {
      throw new Error('启动 Agent 失败: 响应中缺少 agent ID');
    }
    
    const agentId = launchResponse.id;
    log(`Agent 已启动，ID: ${agentId}`, 'green');
    log(`Agent 状态: ${launchResponse.status}`, 'blue');
    log(`查看 Agent: ${launchResponse.target?.url || 'N/A'}`, 'blue');
    
    // 轮询 Agent 状态直到完成
    log('等待 Agent 完成...', 'yellow');
    const statusResponse = await pollAgentStatus(config, agentId, config.maxWaitTime || 300000);
    
    if (statusResponse.status === 'FAILED') {
      throw new Error(`Agent 执行失败: ${statusResponse.summary || '未知错误'}`);
    }
    
    if (statusResponse.status === 'STOPPED') {
      throw new Error('Agent 已被停止');
    }
    
    log(`Agent 已完成，状态: ${statusResponse.status}`, 'green');
    
    // 获取对话内容
    log('获取 Agent 对话内容...', 'yellow');
    const conversationResponse = await getAgentConversation(config, agentId);
    
    // 提取响应内容 - 从对话消息中提取助手回复
    let content = '';
    if (conversationResponse.messages && conversationResponse.messages.length > 0) {
      // 提取所有助手消息
      const assistantMessages = conversationResponse.messages
        .filter(msg => msg.type === 'assistant_message')
        .map(msg => msg.text)
        .join('\n\n');
      content = assistantMessages || statusResponse.summary || '';
    } else {
      content = statusResponse.summary || JSON.stringify(statusResponse, null, 2);
    }
    
    // 保存结果
    if (task.outputFile) {
      // 从 tools/smart/ 目录向上两级到项目根目录
      const projectRoot = path.resolve(__dirname, '../..');
      const outputPath = path.resolve(projectRoot, task.outputFile);
      const outputDir = path.dirname(outputPath);
      
      // 确保输出目录存在
      if (!fs.existsSync(outputDir)) {
        fs.mkdirSync(outputDir, { recursive: true });
      }
      
      fs.writeFileSync(outputPath, content, 'utf-8');
      log(`结果已保存到: ${task.outputFile}`, 'green');
    } else {
      // 如果没有指定输出文件，保存到默认输出目录
      const outputDir = CONFIG.outputDir;
      if (!fs.existsSync(outputDir)) {
        fs.mkdirSync(outputDir, { recursive: true });
      }
      
      const outputPath = path.join(outputDir, `${task.id || `task-${index + 1}`}.md`);
      fs.writeFileSync(outputPath, content, 'utf-8');
      log(`结果已保存到: ${outputPath}`, 'green');
    }
    
    return { success: true, taskId: task.id, content };
  } catch (error) {
    log(`任务失败: ${error.message}`, 'red');
    return { success: false, taskId: task.id, error: error.message };
  }
}

/**
 * 主函数
 */
async function main() {
  log('=== Smart API 批量执行 Agent ===', 'cyan');
  
  // 加载配置
  const config = loadConfig();
  
  // 合并环境变量中的配置（环境变量优先级更高）
  if (process.env.SMART_API_KEY) {
    config.apiKey = process.env.SMART_API_KEY;
  }
  if (process.env.SMART_API_URL) {
    config.apiUrl = process.env.SMART_API_URL;
  }
  if (process.env.SMART_REPOSITORY) {
    config.repository = process.env.SMART_REPOSITORY;
  }
  
  // 如果没有配置 repository，尝试从 git 获取
  if (!config.repository) {
    const gitRepo = getRepositoryFromGit();
    if (gitRepo) {
      config.repository = gitRepo;
      log(`从 git 检测到仓库: ${gitRepo}`, 'green');
    }
  }
  
  // 检查 API Key
  if (!config.apiKey) {
    log('错误: 未设置 API Key', 'red');
    log('请设置 SMART_API_KEY 环境变量或编辑配置文件', 'yellow');
    log('  export SMART_API_KEY="your-api-key-here"', 'cyan');
    process.exit(1);
  }
  
  // 检查 repository
  if (!config.repository) {
    log('错误: 未设置 repository', 'red');
    log('请设置 SMART_REPOSITORY 环境变量或编辑配置文件', 'yellow');
    log('  export SMART_REPOSITORY="https://github.com/your-org/your-repo"', 'cyan');
    log('或者确保项目已初始化 git 并配置了 remote.origin.url', 'yellow');
    process.exit(1);
  }
  
  if (!config.tasks || config.tasks.length === 0) {
    log('错误: 配置文件中没有任务', 'red');
    process.exit(1);
  }
  
  log(`找到 ${config.tasks.length} 个任务`, 'green');
  
  // 确保输出目录存在
  if (!fs.existsSync(CONFIG.outputDir)) {
    fs.mkdirSync(CONFIG.outputDir, { recursive: true });
  }
  
  // 处理所有任务
  const results = [];
  for (let i = 0; i < config.tasks.length; i++) {
    const task = config.tasks[i];
    const result = await processTask(config, task, i, config.tasks.length);
    results.push(result);
    
    // 任务之间的延迟，避免请求过快
    if (i < config.tasks.length - 1 && config.delayBetweenTasks) {
      await new Promise(resolve => setTimeout(resolve, config.delayBetweenTasks));
    }
  }
  
  // 输出统计信息
  log('\n=== 执行完成 ===', 'cyan');
  const successCount = results.filter(r => r.success).length;
  const failCount = results.filter(r => !r.success).length;
  
  log(`成功: ${successCount}`, 'green');
  if (failCount > 0) {
    log(`失败: ${failCount}`, 'red');
  }
  
  // 保存执行报告
  const reportPath = path.join(CONFIG.outputDir, `report-${Date.now()}.json`);
  fs.writeFileSync(reportPath, JSON.stringify({
    timestamp: new Date().toISOString(),
    total: results.length,
    success: successCount,
    failed: failCount,
    results: results
  }, null, 2), 'utf-8');
  
  log(`执行报告已保存到: ${reportPath}`, 'blue');
  
  process.exit(failCount > 0 ? 1 : 0);
}

// 运行主函数
if (require.main === module) {
  main().catch(error => {
    log(`程序执行失败: ${error.message}`, 'red');
    console.error(error);
    process.exit(1);
  });
}

module.exports = { processTask, callSmartAPI, buildPromptWithFiles };

