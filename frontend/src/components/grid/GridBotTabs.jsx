/**
 * GridBotTabs - AI 추천 그리드봇 템플릿
 *
 * AI 탭: 관리자가 만든 템플릿 목록 (TemplateList)
 */
import React from 'react';
import { RobotOutlined } from '@ant-design/icons';
import { TemplateList } from './templates';
import './GridBotTabs.css';

const GridBotTabs = ({
    availableBalance = 0,     // 가용 잔액
    onBotCreated,            // 봇 생성 완료 콜백
}) => {
    return (
        <div className="grid-bot-tabs">
            <div className="ai-tab-header">
                <RobotOutlined style={{ marginRight: 8 }} />
                <span>AI 추천 템플릿</span>
            </div>
            <TemplateList
                availableBalance={availableBalance}
                onBotCreated={onBotCreated}
            />
        </div>
    );
};

export default GridBotTabs;
