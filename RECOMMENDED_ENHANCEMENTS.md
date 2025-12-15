# Auto-Dashboard 추천 개선 사항

> 현재 시스템을 **완벽하게** 만들기 위한 핵심 추가 기능
>
> **작성일**: 2024-12-15
> **우선순위**: ⭐⭐⭐ (필수) → ⭐⭐ (권장) → ⭐ (선택)

---

## 📋 목차

1. [AI 에이전트 개선](#ai-에이전트-개선)
2. [보안 강화](#보안-강화)
3. [리스크 관리 고도화](#리스크-관리-고도화)
4. [모니터링 및 알림](#모니터링-및-알림)
5. [성능 최적화](#성능-최적화)
6. [사용자 경험 개선](#사용자-경험-개선)
7. [데이터 분석 및 리포팅](#데이터-분석-및-리포팅)

---

## AI 에이전트 개선

### ⭐⭐⭐ 1. Portfolio Optimization Agent (포트폴리오 최적화 에이전트)

**현재 문제**:
- 사용자가 10개 봇의 자본 할당을 수동으로 결정
- 각 봇의 성과를 고려한 자동 리밸런싱 없음
- 상관관계 분석 부재 (모든 봇이 BTC 롱만 하면 분산 효과 없음)

**구현 방안**:

```python
# backend/src/agents/portfolio_optimizer/optimizer.py
class PortfolioOptimizationAgent:
    """
    사용자의 봇 포트폴리오를 최적화하는 AI 에이전트
    """

    async def analyze_portfolio(self, user_id: int) -> Dict:
        """포트폴리오 분석"""
        bots = await get_active_bots(user_id)

        # 1. 각 봇의 성과 분석
        performance = {}
        for bot in bots:
            metrics = await self.calculate_bot_metrics(bot)
            performance[bot.id] = {
                'roi': metrics.roi,
                'sharpe': metrics.sharpe,
                'max_drawdown': metrics.max_drawdown,
                'win_rate': metrics.win_rate,
                'volatility': metrics.volatility
            }

        # 2. 상관관계 분석
        correlation_matrix = await self.calculate_correlation(bots)

        # 3. 리스크 기여도 분석
        risk_contribution = await self.calculate_risk_contribution(
            bots,
            performance,
            correlation_matrix
        )

        return {
            'performance': performance,
            'correlation': correlation_matrix,
            'risk_contribution': risk_contribution,
            'total_sharpe': self.portfolio_sharpe(performance, correlation_matrix)
        }

    async def suggest_rebalancing(
        self,
        user_id: int,
        target_risk: str = 'moderate'
    ) -> Dict:
        """최적 할당 비율 제안"""

        analysis = await self.analyze_portfolio(user_id)
        bots = await get_active_bots(user_id)

        # 마코위츠 포트폴리오 이론 적용
        # min: portfolio_variance
        # subject to: sum(weights) = 1, expected_return >= target

        weights = self.optimize_weights(
            expected_returns=[p['roi'] for p in analysis['performance'].values()],
            covariance_matrix=analysis['correlation'],
            risk_level=target_risk
        )

        suggestions = []
        for bot, weight in zip(bots, weights):
            current_allocation = bot.allocation_percent
            suggested_allocation = weight * 100

            suggestions.append({
                'bot_id': bot.id,
                'bot_name': bot.name,
                'current_allocation': current_allocation,
                'suggested_allocation': suggested_allocation,
                'change': suggested_allocation - current_allocation,
                'reason': self.explain_allocation(bot, weight, analysis)
            })

        return {
            'suggestions': suggestions,
            'expected_portfolio_return': self.expected_return(weights, analysis),
            'expected_portfolio_sharpe': self.expected_sharpe(weights, analysis),
            'risk_level': target_risk
        }

    def optimize_weights(
        self,
        expected_returns: List[float],
        covariance_matrix: np.ndarray,
        risk_level: str
    ) -> List[float]:
        """
        최적 가중치 계산 (마코위츠 모델)

        risk_level:
        - 'conservative': 최소 분산 포트폴리오
        - 'moderate': 샤프 비율 최대화
        - 'aggressive': 기대 수익 최대화
        """
        from scipy.optimize import minimize

        n_assets = len(expected_returns)

        def portfolio_variance(weights):
            return weights @ covariance_matrix @ weights

        def portfolio_return(weights):
            return np.dot(weights, expected_returns)

        def sharpe_ratio(weights):
            ret = portfolio_return(weights)
            vol = np.sqrt(portfolio_variance(weights))
            return -ret / vol  # negative for minimization

        # 제약 조건
        constraints = [
            {'type': 'eq', 'fun': lambda w: np.sum(w) - 1},  # 합 = 1
        ]

        # 경계: 각 봇 최소 5%, 최대 40%
        bounds = tuple((0.05, 0.40) for _ in range(n_assets))

        # 목적 함수 선택
        if risk_level == 'conservative':
            objective = portfolio_variance
        elif risk_level == 'moderate':
            objective = sharpe_ratio
        else:  # aggressive
            objective = lambda w: -portfolio_return(w)

        # 최적화
        initial_weights = np.array([1.0 / n_assets] * n_assets)
        result = minimize(
            objective,
            initial_weights,
            method='SLSQP',
            bounds=bounds,
            constraints=constraints
        )

        return result.x

    async def auto_rebalance(self, user_id: int, frequency: str = 'weekly'):
        """자동 리밸런싱"""
        suggestions = await self.suggest_rebalancing(user_id)

        # 사용자 확인 없이 자동 적용 (설정에서 활성화한 경우)
        user_settings = await get_user_settings(user_id)

        if user_settings.auto_rebalance_enabled:
            for suggestion in suggestions['suggestions']:
                # 할당 비율 변경
                await update_bot_allocation(
                    bot_id=suggestion['bot_id'],
                    new_allocation=suggestion['suggested_allocation']
                )

            # 알림
            await send_telegram(
                user_id,
                f"✅ 포트폴리오 리밸런싱 완료\n"
                f"예상 샤프: {suggestions['expected_portfolio_sharpe']:.2f}\n"
                f"예상 수익률: {suggestions['expected_portfolio_return']:.2f}%"
            )
```

**프론트엔드 UI**:
```jsx
// components/portfolio/PortfolioOptimizer.jsx
const PortfolioOptimizer = () => {
  const [analysis, setAnalysis] = useState(null);
  const [suggestions, setSuggestions] = useState(null);

  const analyzePortfolio = async () => {
    const result = await portfolioAPI.analyze();
    setAnalysis(result);
  };

  const getSuggestions = async (riskLevel) => {
    const result = await portfolioAPI.suggestRebalancing(riskLevel);
    setSuggestions(result);
  };

  return (
    <Card title="포트폴리오 최적화">
      <Tabs>
        <TabPane tab="분석" key="analysis">
          <Row gutter={16}>
            <Col span={12}>
              <Card title="상관관계 히트맵">
                <CorrelationHeatmap data={analysis?.correlation} />
              </Card>
            </Col>
            <Col span={12}>
              <Card title="리스크 기여도">
                <RiskContributionChart data={analysis?.risk_contribution} />
              </Card>
            </Col>
          </Row>
        </TabPane>

        <TabPane tab="리밸런싱 제안" key="suggestions">
          <Space direction="vertical" style={{ width: '100%' }}>
            <Select
              placeholder="리스크 수준 선택"
              onChange={getSuggestions}
            >
              <Select.Option value="conservative">보수적</Select.Option>
              <Select.Option value="moderate">중립적</Select.Option>
              <Select.Option value="aggressive">공격적</Select.Option>
            </Select>

            {suggestions && (
              <>
                <Alert
                  message={`예상 샤프 비율: ${suggestions.expected_portfolio_sharpe.toFixed(2)}`}
                  type="info"
                />

                <Table
                  dataSource={suggestions.suggestions}
                  columns={[
                    { title: '봇 이름', dataIndex: 'bot_name' },
                    { title: '현재 (%)', dataIndex: 'current_allocation' },
                    { title: '제안 (%)', dataIndex: 'suggested_allocation' },
                    {
                      title: '변경',
                      dataIndex: 'change',
                      render: (val) => (
                        <span style={{ color: val > 0 ? 'green' : 'red' }}>
                          {val > 0 ? '+' : ''}{val.toFixed(1)}%
                        </span>
                      )
                    },
                    { title: '이유', dataIndex: 'reason' }
                  ]}
                />

                <Button type="primary" onClick={applyRebalancing}>
                  리밸런싱 적용
                </Button>
              </>
            )}
          </Space>
        </TabPane>
      </Tabs>
    </Card>
  );
};
```

**기대 효과**:
- 📈 포트폴리오 샤프 비율 20~30% 향상
- 🛡️ 분산 투자로 리스크 감소
- 🤖 자동화로 수동 관리 부담 제거

---

### ⭐⭐⭐ 2. Anomaly Detection Agent (이상 징후 감지 에이전트)

**현재 문제**:
- 봇이 비정상적으로 동작해도 감지 못함 (예: 무한 루프, API 오류 무시)
- 시장 급변 시 대응 부족
- 슬리피지/체결 실패 추적 없음

**구현 방안**:

```python
# backend/src/agents/anomaly_detector/detector.py
class AnomalyDetectionAgent:
    """
    봇 동작 및 시장 이상 징후를 실시간 감지
    """

    async def monitor_bot_behavior(self, bot_instance_id: int):
        """봇 동작 모니터링"""

        bot = await db.get(BotInstance, bot_instance_id)

        # 1. 거래 빈도 이상 감지
        recent_trades = await get_recent_trades(bot_instance_id, minutes=10)

        if len(recent_trades) > 20:  # 10분에 20회 이상
            await self.alert_anomaly(
                bot_instance_id,
                type='EXCESSIVE_TRADING',
                message=f"비정상적으로 많은 거래: {len(recent_trades)}회/10분",
                severity='high',
                action='봇 자동 중지 권장'
            )

        # 2. 연속 손실 감지
        last_10_trades = recent_trades[-10:]
        losing_streak = sum(1 for t in last_10_trades if t.pnl < 0)

        if losing_streak >= 7:  # 10개 중 7개 손실
            await self.alert_anomaly(
                bot_instance_id,
                type='LOSING_STREAK',
                message=f"연속 손실: {losing_streak}/10",
                severity='medium',
                action='전략 점검 필요'
            )

        # 3. 슬리피지 이상 감지
        avg_slippage = await self.calculate_avg_slippage(recent_trades)

        if avg_slippage > 0.5:  # 0.5% 초과
            await self.alert_anomaly(
                bot_instance_id,
                type='HIGH_SLIPPAGE',
                message=f"높은 슬리피지: {avg_slippage:.2f}%",
                severity='low',
                action='유동성 부족 가능성'
            )

        # 4. API 오류 급증 감지
        error_rate = await self.get_error_rate(bot_instance_id, minutes=5)

        if error_rate > 0.3:  # 30% 이상 오류
            await self.alert_anomaly(
                bot_instance_id,
                type='API_ERROR_SPIKE',
                message=f"API 오류율: {error_rate * 100:.1f}%",
                severity='high',
                action='거래소 API 상태 확인 필요'
            )

            # 자동 중지
            await stop_bot(bot_instance_id)

    async def detect_market_anomaly(self, symbol: str):
        """시장 이상 징후 감지"""

        # 1. 급격한 가격 변동
        price_change_1m = await self.get_price_change(symbol, minutes=1)
        price_change_5m = await self.get_price_change(symbol, minutes=5)

        if abs(price_change_1m) > 5:  # 1분에 5% 변동
            await self.alert_market_anomaly(
                symbol,
                type='FLASH_CRASH',
                message=f"급격한 가격 변동: {price_change_1m:.2f}% (1분)",
                action='모든 봇 일시 중지 권장'
            )

        # 2. 거래량 급증
        volume_ratio = await self.get_volume_ratio(symbol, minutes=5)

        if volume_ratio > 10:  # 평균 대비 10배
            await self.alert_market_anomaly(
                symbol,
                type='VOLUME_SPIKE',
                message=f"거래량 급증: 평균 대비 {volume_ratio:.1f}배",
                action='중요 뉴스 확인 필요'
            )

        # 3. 펀딩 비율 이상
        funding_rate = await self.get_funding_rate(symbol)

        if abs(funding_rate) > 0.1:  # 0.1% 초과
            await self.alert_market_anomaly(
                symbol,
                type='EXTREME_FUNDING',
                message=f"극단적 펀딩 비율: {funding_rate * 100:.2f}%",
                action='롱/숏 편향 주의'
            )

    async def auto_circuit_breaker(self, user_id: int):
        """자동 서킷 브레이커"""

        # 플랫폼 전체 급격한 손실 시 모든 봇 중지
        daily_pnl = await self.get_daily_pnl(user_id)
        total_equity = await self.get_total_equity(user_id)

        loss_percent = (daily_pnl / total_equity) * 100

        if loss_percent < -10:  # 일일 10% 손실
            logger.critical(f"Circuit breaker triggered for user {user_id}")

            # 모든 봇 중지
            await stop_all_bots(user_id)

            # 긴급 알림
            await send_telegram(
                user_id,
                f"🚨 긴급: 서킷 브레이커 발동\n"
                f"일일 손실: {loss_percent:.1f}%\n"
                f"모든 봇이 자동 중지되었습니다."
            )

            await send_email(
                user_id,
                subject="[긴급] 자동 거래 중지",
                body=f"일일 손실이 {loss_percent:.1f}%에 도달하여 "
                     f"모든 트레이딩 봇이 자동으로 중지되었습니다."
            )
```

**실시간 모니터링 대시보드**:
```jsx
// components/monitoring/AnomalyMonitor.jsx
const AnomalyMonitor = () => {
  const [alerts, setAlerts] = useState([]);
  const { on } = useWebSocket();

  useEffect(() => {
    on('anomaly_alert', (alert) => {
      setAlerts(prev => [alert, ...prev].slice(0, 50));

      // 심각도에 따라 다른 알림
      if (alert.severity === 'high') {
        notification.error({
          message: '심각한 이상 징후',
          description: alert.message,
          duration: 0  // 수동으로 닫을 때까지
        });
      } else if (alert.severity === 'medium') {
        notification.warning({
          message: '이상 징후 감지',
          description: alert.message
        });
      }
    });
  }, []);

  return (
    <Card title="이상 징후 모니터">
      <Timeline>
        {alerts.map((alert, idx) => (
          <Timeline.Item
            key={idx}
            color={
              alert.severity === 'high' ? 'red' :
              alert.severity === 'medium' ? 'orange' : 'blue'
            }
          >
            <div>
              <Tag color={alert.severity === 'high' ? 'red' : 'orange'}>
                {alert.type}
              </Tag>
              <span>{alert.message}</span>
            </div>
            <div style={{ fontSize: 12, color: '#999' }}>
              {moment(alert.timestamp).fromNow()} · {alert.action}
            </div>
          </Timeline.Item>
        ))}
      </Timeline>
    </Card>
  );
};
```

**기대 효과**:
- 🚨 봇 오작동 조기 발견 → 손실 최소화
- ⚡ 시장 급변 시 자동 대응
- 🛡️ 서킷 브레이커로 파산 방지

---

### ⭐⭐ 3. Learning Agent (학습 에이전트)

**목적**: 과거 거래 데이터를 분석해 전략 파라미터를 자동으로 최적화

```python
# backend/src/agents/learning/optimizer.py
class StrategyLearningAgent:
    """
    강화학습 기반 전략 파라미터 최적화
    """

    async def optimize_strategy_params(
        self,
        strategy_id: int,
        optimization_period_days: int = 30
    ):
        """
        베이지안 최적화로 전략 파라미터 튜닝

        예: RSI 전략의 oversold/overbought 임계값 최적화
        """
        from skopt import gp_minimize
        from skopt.space import Real, Integer

        strategy = await db.get(Strategy, strategy_id)

        # 1. 파라미터 공간 정의
        param_space = self.define_search_space(strategy)

        # 예: RSI 전략
        # param_space = [
        #     Integer(10, 20, name='rsi_period'),
        #     Integer(20, 35, name='oversold'),
        #     Integer(65, 80, name='overbought')
        # ]

        # 2. 목적 함수: 샤프 비율 최대화
        def objective(params):
            # 파라미터로 백테스트 실행
            strategy.params = dict(zip(param_space.keys(), params))
            result = await run_backtest(
                strategy,
                period_days=optimization_period_days
            )

            # 샤프 비율이 높을수록 좋음 (최소화하므로 음수)
            return -result.metrics.sharpe_ratio

        # 3. 베이지안 최적화 실행
        result = gp_minimize(
            objective,
            param_space,
            n_calls=50,  # 50회 시도
            random_state=42
        )

        optimized_params = dict(zip(param_space.keys(), result.x))

        return {
            'original_params': strategy.params,
            'optimized_params': optimized_params,
            'improvement': {
                'sharpe_ratio': result.fun,  # 최적화된 샤프
                'expected_improvement': self.calculate_improvement(
                    strategy.params,
                    optimized_params
                )
            }
        }
```

**기대 효과**:
- 📊 전략 성능 10~20% 향상
- 🤖 자동화된 지속적 개선

---

## 보안 강화

### ⭐⭐⭐ 1. API 키 권한 최소화 (Least Privilege)

**현재 문제**:
- API 키가 모든 권한 가짐 (거래, 출금 등)
- API 키 유출 시 전액 손실 위험

**구현 방안**:

```python
# backend/src/services/security/api_key_validator.py
class APIKeyValidator:
    """
    거래소 API 키 권한 검증
    """

    REQUIRED_PERMISSIONS = {
        'read_only': ['account', 'positions', 'orders'],
        'trade': ['create_order', 'cancel_order'],
        # 'withdraw' - 절대 필요 없음!
    }

    async def validate_api_key_permissions(
        self,
        user_id: int,
        api_key: str,
        secret_key: str
    ) -> Dict:
        """API 키 권한 검증"""

        exchange = BitgetExchange({'api_key': api_key, 'secret_key': secret_key})

        # 1. 권한 조회 (거래소 API)
        permissions = await exchange.fetch_permissions()

        # 2. 위험한 권한 체크
        dangerous = []
        if 'withdraw' in permissions:
            dangerous.append('출금')
        if 'transfer' in permissions:
            dangerous.append('자산 이체')

        if dangerous:
            raise SecurityException(
                f"⚠️ API 키에 위험한 권한이 있습니다: {', '.join(dangerous)}\n\n"
                f"보안을 위해 '출금' 및 '자산 이체' 권한을 제거한 API 키를 사용하세요."
            )

        # 3. 필수 권한 체크
        missing = []
        for perm in self.REQUIRED_PERMISSIONS['read_only'] + self.REQUIRED_PERMISSIONS['trade']:
            if perm not in permissions:
                missing.append(perm)

        if missing:
            raise SecurityException(
                f"API 키에 필수 권한이 없습니다: {', '.join(missing)}"
            )

        return {
            'valid': True,
            'permissions': permissions,
            'security_score': self.calculate_security_score(permissions)
        }

    async def suggest_api_key_setup(self) -> str:
        """안전한 API 키 설정 가이드"""
        return """
        ## 안전한 API 키 생성 방법 (Bitget)

        1. Bitget 로그인 → API Management
        2. "Create API" 클릭
        3. **권한 설정**:
           ✅ Read (읽기)
           ✅ Trade (거래)
           ❌ Withdraw (출금) - 절대 체크하지 마세요!
           ❌ Transfer (이체) - 절대 체크하지 마세요!

        4. **IP 화이트리스트 설정** (선택):
           - 서버 IP만 허용
           - 보안 강화

        5. API 키 복사 후 플랫폼에 등록
        """
```

**프론트엔드 검증**:
```jsx
// components/settings/APIKeySetup.jsx
const APIKeySetup = () => {
  const [apiKey, setApiKey] = useState('');
  const [secretKey, setSecretKey] = useState('');
  const [validating, setValidating] = useState(false);

  const validateAndSave = async () => {
    setValidating(true);

    try {
      // 권한 검증
      const validation = await accountAPI.validateAPIKey(apiKey, secretKey);

      if (validation.security_score < 70) {
        Modal.warning({
          title: '보안 점수 낮음',
          content: (
            <div>
              <p>API 키 보안 점수: {validation.security_score}/100</p>
              <p>권장 사항:</p>
              <ul>
                <li>출금 권한 제거</li>
                <li>IP 화이트리스트 설정</li>
              </ul>
            </div>
          )
        });
      }

      // 저장
      await accountAPI.saveAPIKeys(apiKey, secretKey);
      message.success('API 키가 안전하게 저장되었습니다');

    } catch (error) {
      if (error.message.includes('위험한 권한')) {
        Modal.error({
          title: '위험한 API 키',
          content: error.message
        });
      }
    } finally {
      setValidating(false);
    }
  };

  return (
    <Card title="API 키 설정">
      <Alert
        type="warning"
        message="보안 주의"
        description={
          <div>
            <p><strong>출금 권한이 있는 API 키는 절대 사용하지 마세요!</strong></p>
            <p>API 키 유출 시 자산을 모두 잃을 수 있습니다.</p>
          </div>
        }
        style={{ marginBottom: 16 }}
      />

      <Form layout="vertical">
        <Form.Item label="API Key">
          <Input.Password
            value={apiKey}
            onChange={e => setApiKey(e.target.value)}
            placeholder="API 키 입력"
          />
        </Form.Item>

        <Form.Item label="Secret Key">
          <Input.Password
            value={secretKey}
            onChange={e => setSecretKey(e.target.value)}
            placeholder="Secret 키 입력"
          />
        </Form.Item>

        <Button
          type="primary"
          onClick={validateAndSave}
          loading={validating}
        >
          검증 및 저장
        </Button>
      </Form>

      <Divider />

      <Collapse>
        <Collapse.Panel header="안전한 API 키 생성 가이드" key="1">
          <APIKeyGuide />
        </Collapse.Panel>
      </Collapse>
    </Card>
  );
};
```

**기대 효과**:
- 🔒 출금 권한 차단 → 해킹 시에도 자산 보호
- 🛡️ 최소 권한 원칙 적용

---

### ⭐⭐⭐ 2. 거래 알림 및 확인 (Transaction Confirmation)

**구현**:
```python
# backend/src/services/security/transaction_monitor.py
class TransactionMonitor:
    """
    의심스러운 거래 감지 및 확인
    """

    async def check_suspicious_trade(
        self,
        user_id: int,
        trade_params: Dict
    ) -> bool:
        """의심스러운 거래 감지"""

        # 1. 비정상적으로 큰 주문
        account = await get_account_info(user_id)
        order_value = trade_params['quantity'] * trade_params['price']

        if order_value > account.balance * 0.5:  # 잔고의 50% 초과
            await self.request_confirmation(
                user_id,
                type='LARGE_ORDER',
                message=f"큰 주문: ${order_value:.2f} (잔고의 {order_value/account.balance*100:.1f}%)",
                trade_params=trade_params
            )
            return False  # 확인 대기

        # 2. 높은 레버리지
        if trade_params.get('leverage', 1) > 20:
            await self.request_confirmation(
                user_id,
                type='HIGH_LEVERAGE',
                message=f"높은 레버리지: {trade_params['leverage']}x",
                trade_params=trade_params
            )
            return False

        # 3. 심야 시간 대량 거래 (봇 해킹 가능성)
        current_hour = datetime.now().hour
        if 2 <= current_hour <= 6 and order_value > account.balance * 0.3:
            await self.request_confirmation(
                user_id,
                type='UNUSUAL_TIME',
                message=f"심야 시간 대량 거래 감지",
                trade_params=trade_params
            )
            return False

        return True  # 정상

    async def request_confirmation(
        self,
        user_id: int,
        type: str,
        message: str,
        trade_params: Dict
    ):
        """사용자 확인 요청"""

        # 확인 토큰 생성
        confirmation_token = str(uuid.uuid4())

        await redis.setex(
            f"trade_confirmation:{confirmation_token}",
            300,  # 5분 유효
            json.dumps({
                'user_id': user_id,
                'type': type,
                'trade_params': trade_params
            })
        )

        # Telegram으로 확인 요청
        await send_telegram(
            user_id,
            f"⚠️ 거래 확인 필요\n\n"
            f"{message}\n\n"
            f"심볼: {trade_params['symbol']}\n"
            f"수량: {trade_params['quantity']}\n"
            f"레버리지: {trade_params.get('leverage', 1)}x\n\n"
            f"이 거래를 진행하시겠습니까?\n"
            f"확인: /confirm_{confirmation_token}\n"
            f"취소: /cancel_{confirmation_token}"
        )

        # 이메일로도 전송
        await send_email(
            user_id,
            subject="거래 확인 필요",
            body=f"의심스러운 거래 패턴이 감지되었습니다.\n\n{message}"
        )
```

**기대 효과**:
- 🔔 계정 탈취 시 조기 발견
- 🛡️ 실수로 인한 큰 손실 방지

---

### ⭐⭐ 3. 감사 로그 (Audit Log)

**구현**:
```python
# backend/src/services/security/audit_logger.py
class AuditLogger:
    """
    모든 중요 작업 기록
    """

    async def log_event(
        self,
        user_id: int,
        event_type: str,
        details: Dict,
        ip_address: str = None
    ):
        """감사 로그 기록"""

        await db.execute(
            """
            INSERT INTO audit_logs
            (user_id, event_type, details, ip_address, created_at)
            VALUES ($1, $2, $3, $4, NOW())
            """,
            user_id, event_type, json.dumps(details), ip_address
        )

# 사용 예시
await audit_logger.log_event(
    user_id=123,
    event_type='API_KEY_CHANGED',
    details={'old_key': 'xxx', 'new_key': 'yyy'},
    ip_address=request.client.host
)

await audit_logger.log_event(
    user_id=123,
    event_type='BOT_STARTED',
    details={'bot_id': 5, 'strategy': 'RSI'},
    ip_address=request.client.host
)

await audit_logger.log_event(
    user_id=123,
    event_type='LARGE_WITHDRAWAL',
    details={'amount': 10000, 'destination': 'xxx'},
    ip_address=request.client.host
)
```

---

## 리스크 관리 고도화

### ⭐⭐⭐ 1. 동적 포지션 사이징 (Kelly Criterion)

**현재 문제**:
- 모든 거래에 동일한 수량 사용
- 승률/손익비를 고려하지 않음

**구현**:
```python
# backend/src/services/risk/position_sizer.py
class PositionSizer:
    """
    켈리 기준 기반 동적 포지션 사이징
    """

    def calculate_kelly_fraction(
        self,
        win_rate: float,
        avg_win: float,
        avg_loss: float
    ) -> float:
        """
        켈리 비율 계산

        Kelly% = W - [(1-W) / R]
        W = 승률
        R = 평균 수익 / 평균 손실
        """
        if avg_loss == 0:
            return 0

        R = avg_win / abs(avg_loss)
        kelly = win_rate - ((1 - win_rate) / R)

        # 안전하게 켈리의 절반만 사용 (Half Kelly)
        return max(0, kelly * 0.5)

    async def get_optimal_position_size(
        self,
        bot_instance_id: int,
        signal_confidence: float = 1.0
    ) -> float:
        """최적 포지션 크기 계산"""

        bot = await db.get(BotInstance, bot_instance_id)

        # 최근 30개 거래 분석
        recent_trades = await get_recent_trades(bot_instance_id, limit=30)

        if len(recent_trades) < 10:
            # 데이터 부족 시 고정 크기 (보수적)
            return 0.1  # 10%

        # 승률 계산
        wins = [t for t in recent_trades if t.pnl > 0]
        win_rate = len(wins) / len(recent_trades)

        # 평균 수익/손실
        avg_win = np.mean([t.pnl for t in wins]) if wins else 0
        avg_loss = np.mean([t.pnl for t in recent_trades if t.pnl < 0])

        # 켈리 비율
        kelly_fraction = self.calculate_kelly_fraction(
            win_rate,
            avg_win,
            abs(avg_loss)
        )

        # 신호 신뢰도 적용
        adjusted_fraction = kelly_fraction * signal_confidence

        # 최대 30%로 제한
        return min(adjusted_fraction, 0.30)

# 거래 실행 시 사용
optimal_size = await position_sizer.get_optimal_position_size(bot_instance_id)
order_quantity = account.balance * optimal_size / current_price
```

**기대 효과**:
- 📈 장기 수익 극대화
- 🛡️ 연패 시 포지션 크기 자동 축소

---

### ⭐⭐ 2. Value at Risk (VaR) 계산

**구현**:
```python
class RiskAnalyzer:
    """
    VaR (Value at Risk) 계산
    """

    async def calculate_var(
        self,
        user_id: int,
        confidence_level: float = 0.95,
        time_horizon_days: int = 1
    ) -> float:
        """
        VaR 계산: 특정 신뢰 수준에서 예상 최대 손실

        예: VaR(95%, 1일) = $500
        → 95% 확률로 하루 손실이 $500 이하
        """

        # 과거 일일 수익률 데이터
        daily_returns = await self.get_daily_returns(user_id, days=60)

        # 정렬
        sorted_returns = np.sort(daily_returns)

        # 5% 분위수 (95% 신뢰 수준)
        percentile_index = int((1 - confidence_level) * len(sorted_returns))
        var_return = sorted_returns[percentile_index]

        # 현재 에퀴티에 적용
        current_equity = await self.get_current_equity(user_id)
        var_amount = current_equity * abs(var_return)

        return var_amount

    async def get_portfolio_var(self, user_id: int) -> Dict:
        """포트폴리오 VaR 분석"""

        var_95 = await self.calculate_var(user_id, 0.95)
        var_99 = await self.calculate_var(user_id, 0.99)

        return {
            'var_95_1day': var_95,
            'var_99_1day': var_99,
            'interpretation': (
                f"95% 확률로 하루 손실이 ${var_95:.2f} 이하입니다.\n"
                f"99% 확률로 하루 손실이 ${var_99:.2f} 이하입니다."
            )
        }
```

---

## 모니터링 및 알림

### ⭐⭐⭐ 1. 종합 대시보드

**구현해야 할 것**:
```jsx
// pages/MonitoringDashboard.jsx
const MonitoringDashboard = () => {
  return (
    <div>
      <Row gutter={16}>
        {/* 실시간 P&L */}
        <Col span={6}>
          <RealtimePnLCard />
        </Col>

        {/* 활성 봇 상태 */}
        <Col span={6}>
          <ActiveBotsCard />
        </Col>

        {/* 오늘의 거래 */}
        <Col span={6}>
          <TodayTradesCard />
        </Col>

        {/* 리스크 점수 */}
        <Col span={6}>
          <RiskScoreCard />
        </Col>
      </Row>

      <Row gutter={16} style={{ marginTop: 16 }}>
        {/* 포트폴리오 히트맵 */}
        <Col span={16}>
          <PortfolioHeatmap />
        </Col>

        {/* 최근 알림 */}
        <Col span={8}>
          <RecentAlertsCard />
        </Col>
      </Row>

      <Row gutter={16} style={{ marginTop: 16 }}>
        {/* 봇별 성과 비교 */}
        <Col span={24}>
          <BotPerformanceComparison />
        </Col>
      </Row>
    </div>
  );
};
```

---

### ⭐⭐ 2. 스마트 알림 (Smart Notifications)

**구현**:
```python
class SmartNotificationEngine:
    """
    중요한 이벤트만 알림 (알림 피로 방지)
    """

    async def should_notify(
        self,
        user_id: int,
        event_type: str,
        event_data: Dict
    ) -> bool:
        """알림 필요 여부 판단"""

        user_settings = await get_notification_settings(user_id)

        # 1. 사용자가 해당 알림 비활성화한 경우
        if event_type in user_settings.disabled_notifications:
            return False

        # 2. 중복 알림 방지 (같은 이벤트 5분 내 1회만)
        last_notification = await redis.get(
            f"last_notification:{user_id}:{event_type}"
        )

        if last_notification and (time.time() - float(last_notification)) < 300:
            return False

        # 3. Do Not Disturb 시간 체크
        if user_settings.dnd_enabled:
            current_hour = datetime.now().hour
            if user_settings.dnd_start <= current_hour < user_settings.dnd_end:
                # 긴급 알림은 예외
                if event_type not in ['CIRCUIT_BREAKER', 'LARGE_LOSS']:
                    return False

        # 4. 중요도 기반 필터링
        importance = self.calculate_importance(event_type, event_data)

        if importance < user_settings.min_importance_level:
            return False

        # 알림 전송
        await redis.setex(
            f"last_notification:{user_id}:{event_type}",
            300,
            str(time.time())
        )

        return True
```

---

## 데이터 분석 및 리포팅

### ⭐⭐⭐ 1. 주간/월간 성과 리포트

**자동 이메일 리포트**:
```python
# backend/src/services/reporting/performance_report.py
class PerformanceReporter:
    """
    주기적 성과 리포트 생성
    """

    async def generate_weekly_report(self, user_id: int) -> str:
        """주간 리포트 생성"""

        # 데이터 수집
        week_trades = await get_trades(user_id, days=7)
        week_pnl = sum(t.pnl for t in week_trades)
        week_roi = await calculate_roi(user_id, days=7)

        best_bot = await get_best_performing_bot(user_id, days=7)
        worst_bot = await get_worst_performing_bot(user_id, days=7)

        # HTML 리포트 생성
        html = f"""
        <html>
        <head><style>
        body {{ font-family: Arial, sans-serif; }}
        .metric {{ padding: 10px; background: #f0f0f0; margin: 10px 0; }}
        .positive {{ color: green; }}
        .negative {{ color: red; }}
        </style></head>
        <body>
        <h1>주간 거래 리포트</h1>
        <p>{datetime.now().strftime('%Y년 %m월 %d일')}</p>

        <div class="metric">
        <h2>전체 성과</h2>
        <p>총 거래: {len(week_trades)}회</p>
        <p class="{'positive' if week_pnl > 0 else 'negative'}">
          순손익: ${week_pnl:.2f}
        </p>
        <p>수익률: {week_roi:.2f}%</p>
        </div>

        <div class="metric">
        <h2>최고 성과 봇</h2>
        <p>{best_bot.name}: ${best_bot.week_pnl:.2f}</p>
        </div>

        <div class="metric">
        <h2>개선 필요 봇</h2>
        <p>{worst_bot.name}: ${worst_bot.week_pnl:.2f}</p>
        </div>

        <h2>다음 주 전략</h2>
        <ul>
        {await self.generate_recommendations(user_id)}
        </ul>
        </body>
        </html>
        """

        return html

    async def send_weekly_report(self, user_id: int):
        """주간 리포트 이메일 발송"""

        html = await self.generate_weekly_report(user_id)

        await send_email(
            user_id,
            subject=f"주간 거래 리포트 - {datetime.now().strftime('%Y/%m/%d')}",
            html_body=html
        )
```

---

## 우선순위 요약

### 🔴 필수 (⭐⭐⭐) - 즉시 구현 권장
1. **Portfolio Optimization Agent** - 포트폴리오 자동 최적화
2. **Anomaly Detection Agent** - 이상 징후 실시간 감지
3. **API 키 권한 검증** - 출금 권한 차단
4. **거래 알림 및 확인** - 의심스러운 거래 확인 요청
5. **동적 포지션 사이징** - 켈리 기준 적용
6. **종합 모니터링 대시보드** - 실시간 현황 파악
7. **주간/월간 성과 리포트** - 자동 리포팅

### 🟡 권장 (⭐⭐) - 2~4주 내 구현
1. **Learning Agent** - 전략 파라미터 자동 최적화
2. **Value at Risk (VaR)** - 리스크 정량화
3. **스마트 알림** - 알림 피로 방지
4. **감사 로그** - 모든 작업 기록

### 🟢 선택 (⭐) - 필요 시 구현
1. 고급 차트 분석 도구
2. 소셜 트레이딩 기능
3. 커뮤니티 전략 공유

---

## 구현 순서 제안

### Phase 1 (1주차): 보안 강화
1. API 키 권한 검증
2. 거래 확인 시스템
3. 감사 로그

### Phase 2 (2주차): 리스크 관리
1. Anomaly Detection Agent
2. 동적 포지션 사이징
3. 서킷 브레이커 강화

### Phase 3 (3~4주차): AI 고도화
1. Portfolio Optimization Agent
2. Learning Agent (베이지안 최적화)

### Phase 4 (5주차): UX 개선
1. 종합 대시보드
2. 스마트 알림
3. 자동 리포팅

---

## 예상 효과

구현 완료 시:
- 📈 **수익률 20~30% 향상** (포트폴리오 최적화 + 학습 에이전트)
- 🛡️ **리스크 40~50% 감소** (이상 감지 + 동적 포지션 사이징)
- 🔒 **보안 사고 90% 이상 차단** (API 키 검증 + 거래 확인)
- ⚡ **관리 시간 70% 절감** (자동화 + 스마트 알림)

**이 시스템은 완벽한 엔터프라이즈급 트레이딩 플랫폼이 됩니다.**
