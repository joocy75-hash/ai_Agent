/**
 * Trading Page - 봇 마켓플레이스
 *
 * Bitget 스타일 다크 테마 봇 선택 페이지
 * 사용자가 전략 템플릿을 선택하고 금액만 입력하면 봇이 시작됨
 */
import React from 'react';
import { BotMarketplace } from '../components/trading';
import './Trading.css';

export default function Trading() {
    return (
        <div className="trading-page dark-theme">
            <BotMarketplace />
        </div>
    );
}
