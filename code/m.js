// ==UserScript==
// @name         处理车辆选择 Picker
// @namespace    https://tampermonkey.net/
// @version      1.0
// @description  点击“切换车辆”按钮后，保留 Picker 最后三项
// @match        https://smart-tallyman.cookhere.com/*
// @grant        none
// ==/UserScript==

(function() {
    'use strict';

    // 备用方法：使用隐藏方式处理 Picker，保持原始功能
    function handlePickerFallback() {
        console.log('使用备用方法处理 Picker...');
        const wrapper = document.querySelector('ul.van-picker-column__wrapper') ||
                        document.querySelector('.van-picker-column__wrapper') ||
                        document.querySelector('.van-picker-column ul');
        
        if (wrapper) {
            const items = Array.from(wrapper.querySelectorAll('li'));
            console.log(`备用方法：找到 ${items.length} 个选项`);
            
            if (items.length >= 3) {
                // 隐藏前面的项目，显示最后三项
                items.forEach((item, index) => {
                    if (index < items.length - 3) {
                        // 使用 CSS 隐藏，但保持在 DOM 中以维持 picker 功能
                        item.style.position = 'absolute';
                        item.style.left = '-9999px';
                        item.style.visibility = 'hidden';
                        item.style.opacity = '0';
                        item.style.pointerEvents = 'none';
                        item.setAttribute('aria-hidden', 'true');
                    } else {
                        // 确保最后三项可见且可点击
                        item.style.position = '';
                        item.style.left = '';
                        item.style.visibility = 'visible';
                        item.style.opacity = '1';
                        item.style.pointerEvents = 'auto';
                        item.style.display = '';
                        item.removeAttribute('aria-hidden');
                        
                        // 确保点击功能正常
                        item.style.cursor = 'pointer';
                        
                        console.log(`备用方法显示项目: ${item.textContent.trim()}`);
                        
                        // 添加调试点击事件
                        item.addEventListener('click', function(e) {
                            console.log('备用方法：检测到点击事件:', this.textContent.trim());
                        }, { once: false });
                    }
                });
                console.log('备用方法处理完成，保持点击功能');
            }
        }
    }

    // 处理 Picker 逻辑，保留最后三项
    function handlePicker() {
        console.log('开始处理 Picker，优先使用隐藏方法保持功能完整性...');
        
        // 首先尝试备用方法（隐藏），因为它保持了原始元素和事件
        handlePickerFallback();
        
        // 验证是否成功
        setTimeout(() => {
            const wrapper = document.querySelector('ul.van-picker-column__wrapper') ||
                            document.querySelector('.van-picker-column__wrapper') ||
                            document.querySelector('.van-picker-column ul');
            
            if (wrapper) {
                const visibleItems = Array.from(wrapper.querySelectorAll('li')).filter(item => {
                    const style = window.getComputedStyle(item);
                    return style.display !== 'none' && style.visibility !== 'hidden' && style.opacity !== '0';
                });
                
                console.log(`处理完成，可见选项数: ${visibleItems.length}`);
                visibleItems.forEach((item, index) => {
                    console.log(`可见选项 ${index + 1}: ${item.textContent.trim()}`);
                });
                
                // 如果隐藏方法失败，尝试重建方法
                if (visibleItems.length === 0) {
                    console.log('隐藏方法失败，尝试重建方法...');
                    handlePickerRebuild();
                }
            }
        }, 200);
    }

    // 重建方法作为最后的备用方案
    function handlePickerRebuild() {
        console.log('使用重建方法处理 Picker...');
        
        // 尝试多种选择器来找到 picker 容器
        const selectors = [
            'ul.van-picker-column__wrapper',
            '.van-picker-column__wrapper',
            '.van-picker-column ul',
            '.van-picker__columns .van-picker-column ul'
        ];
        
        let wrapper = null;
        for (const selector of selectors) {
            wrapper = document.querySelector(selector);
            if (wrapper) {
                console.log(`找到 Picker 容器，使用选择器: ${selector}`);
                break;
            }
        }
        
        if (wrapper) {
            const items = Array.from(wrapper.querySelectorAll('li'));
            console.log(`重建方法：找到 ${items.length} 个选项`);
            
            if (items.length >= 3) {
                const lastThree = items.slice(-3);
                console.log('重建方法：最后三项内容:', lastThree.map(item => item.textContent.trim()));
                
                // 保存原始容器的属性
                const originalClasses = wrapper.className;
                const originalStyle = wrapper.getAttribute('style') || '';
                
                // 克隆最后三项，保持深度克隆以保留所有属性
                const clonedItems = lastThree.map(item => {
                    const cloned = item.cloneNode(true);
                    // 确保克隆项的样式正确
                    cloned.style.display = '';
                    cloned.style.visibility = 'visible';
                    cloned.style.opacity = '1';
                    
                    // 确保点击功能正常
                    cloned.style.cursor = 'pointer';
                    cloned.style.pointerEvents = 'auto';
                    
                    // 尝试重新绑定点击事件和触摸事件
                    ['click', 'touchstart', 'touchend'].forEach(eventType => {
                        cloned.addEventListener(eventType, function(e) {
                            console.log(`重建方法：检测到 ${eventType} 事件:`, this.textContent.trim());
                            
                            // 查找父级的 van-picker 组件并尝试触发选择
                            const pickerColumn = this.closest('.van-picker-column');
                            if (pickerColumn) {
                                // 创建并分发事件给父组件
                                const customEvent = new CustomEvent('pickerSelect', {
                                    bubbles: true,
                                    detail: { 
                                        text: this.textContent.trim(),
                                        element: this 
                                    }
                                });
                                pickerColumn.dispatchEvent(customEvent);
                            }
                        });
                    });
                    
                    return cloned;
                });
                
                // 清空容器并添加克隆的项目
                wrapper.innerHTML = '';
                clonedItems.forEach((item, index) => {
                    wrapper.appendChild(item);
                    console.log(`重建方法：添加项目 ${index + 1}: ${item.textContent.trim()}`);
                });
                
                // 恢复容器属性
                wrapper.className = originalClasses;
                if (originalStyle) {
                    wrapper.setAttribute('style', originalStyle);
                }
                
                console.log('重建方法：已重建 Picker，保留最后三项，当前项目数:', wrapper.querySelectorAll('li').length);
                
            } else {
                console.log('重建方法：选项数量不足3个，不进行处理');
            }
        } else {
            console.log('重建方法：未找到 Picker 容器，尝试的选择器:', selectors);
        }
    }

    // 智能等待 Picker 出现并处理
    function waitForPickerAndHandle() {
        let attempts = 0;
        const maxAttempts = 20; // 最多等待10秒 (20 * 500ms)
        
        function checkForPicker() {
            attempts++;
            console.log(`第 ${attempts} 次尝试查找 Picker...`);
            
            // 检查是否有 picker 相关元素和选项
            const pickerWrapper = document.querySelector('ul.van-picker-column__wrapper') ||
                                  document.querySelector('.van-picker-column__wrapper') ||
                                  document.querySelector('.van-picker-column ul');
            
            if (pickerWrapper) {
                const items = pickerWrapper.querySelectorAll('li');
                if (items.length > 0) {
                    console.log(`检测到 Picker 存在，包含 ${items.length} 个选项，开始处理...`);
                    // 再等待一小段时间确保完全渲染
                    setTimeout(handlePicker, 300);
                    return;
                } else {
                    console.log('找到 Picker 容器但没有选项，继续等待...');
                }
            }
            
            if (attempts < maxAttempts) {
                setTimeout(checkForPicker, 500);
            } else {
                console.log('等待超时，未检测到 Picker');
            }
        }
        
        // 开始检查
        checkForPicker();
    }

    // 查找并绑定"切换车辆"按钮点击事件
    function setupSwitchVehicleButton() {
        // 通过更可靠的方式查找按钮：先找符合样式的，再筛选文本
        const candidateButtons = document.querySelectorAll(
            'span.text-sm.text-blue-500.mr-1.pt-1[data-v-7f18ebd2]'
        );
        const switchVehicleBtn = Array.from(candidateButtons).find(
            btn => btn.textContent.trim() === '切换车辆'
        );

        if (switchVehicleBtn) {
            console.log('找到"切换车辆"按钮');
            // 绑定点击事件
            switchVehicleBtn.addEventListener('click', () => {
                console.log('点击了"切换车辆"按钮');
                // 使用更智能的等待机制
                waitForPickerAndHandle();
            });
        } else {
            console.log('未找到"切换车辆"按钮');
        }
    }

    // 监听 DOM 变化，确保按钮加载后执行
    const observer = new MutationObserver(() => {
        setupSwitchVehicleButton();
    });

    // 启动 MutationObserver，监听 body 及其子元素变化
    observer.observe(document.body, {
        childList: true,
        subtree: true
    });

    // 初始加载时先尝试查找一次
    setupSwitchVehicleButton();
})();