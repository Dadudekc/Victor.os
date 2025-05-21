import unittest
from unittest.mock import Mock, patch, AsyncMock
import json
import os
from datetime import datetime, timedelta
import pytest
import discord
from basicbot.tbow_discord import TBOWDiscord, AlertRule, AlertManager, parse_conditions, DigestManager, PriceCache, AlertLogger

class TestTBOWDiscord(unittest.TestCase):
    def setUp(self):
        """Set up test environment"""
        self.tactics = Mock()
        self.tactics.get_trade_plan = Mock(return_value={
            'bias': 'BULLISH',
            'confidence': 'A+',
            'setup_criteria': ['MACD curl', 'VWAP confirmed'],
            'levels': {'entry': 215.50, 'stop': 212.00, 'target': 225.00},
            'rr_ratio': 2.5,
            'market_context': {'vix': 15.2, 'gap': 0.5, 'volume': 1.2}
        })
        
        self.tactics.get_status = Mock(return_value={
            'price': 475.25,
            'change': 0.5,
            'volume': 1.1,
            'macd': 'BULLISH',
            'rsi': 58.5,
            'vwap': 'ABOVE'
        })
        
        self.tactics.get_stats = Mock(return_value={
            'win_rate': 65.0,
            'avg_rr': 2.1,
            'checklist_compliance': 4.8,
            'emotion_profile': {
                'hesitant': 5,
                'confident': 30,
                'rushed': 8,
                'patient': 7
            }
        })
        
        self.bot = TBOWDiscord(self.tactics)
        self.bot.tactics = self.tactics
        
        # Create test directories
        os.makedirs('runtime', exist_ok=True)
        os.makedirs('runtime/digests', exist_ok=True)
        
        # Create test alert file
        self.alert_file = 'runtime/alerts.json'
        with open(self.alert_file, 'w') as f:
            json.dump([], f)
        
        # Create test alert log
        self.alert_log = 'runtime/alert_log.csv'
        with open(self.alert_log, 'w', newline='') as f:
            f.write('alert_id,symbol,conditions,fired_ts,price_at_fire,price_after_30m\n')

    def tearDown(self):
        """Clean up test environment"""
        if os.path.exists(self.alert_file):
            os.remove(self.alert_file)
        if os.path.exists(self.alert_log):
            os.remove(self.alert_log)
        if os.path.exists('runtime/digests'):
            for file in os.listdir('runtime/digests'):
                os.remove(os.path.join('runtime/digests', file))
            os.rmdir('runtime/digests')
        if os.path.exists('runtime'):
            os.rmdir('runtime')

    def test_parse_conditions(self):
        """Test condition parsing"""
        # Test valid conditions
        conditions = parse_conditions("MACD_curl_up && RSI_below_40")
        self.assertEqual(conditions, ["MACD_curl_up", "RSI_below_40"])
        
        # Test single condition
        conditions = parse_conditions("VWAP_above")
        self.assertEqual(conditions, ["VWAP_above"])
        
        # Test invalid condition
        with self.assertRaises(ValueError):
            parse_conditions("MACD_curl_up && INVALID_CONDITION")

    @pytest.mark.asyncio
    async def test_trade_plan_command(self):
        """Test !tbow plan command"""
        ctx = AsyncMock()
        ctx.send = AsyncMock()
        
        await self.bot.tbow(ctx, 'plan', 'TSLA')
        
        # Verify command processing
        self.tactics.get_trade_plan.assert_called_once_with('TSLA')
        ctx.send.assert_called_once()
        
        # Verify embed content
        embed = ctx.send.call_args[0][0]
        self.assertIsInstance(embed, discord.Embed)
        self.assertIn('TSLA', embed.title)
        self.assertIn('BULLISH', embed.description)
        self.assertIn('2.5:1', embed.description)

    @pytest.mark.asyncio
    async def test_status_command(self):
        """Test !tbow status command"""
        ctx = AsyncMock()
        ctx.send = AsyncMock()
        
        await self.bot.tbow(ctx, 'status', 'SPY')
        
        # Verify command processing
        self.tactics.get_status.assert_called_once_with('SPY')
        ctx.send.assert_called_once()
        
        # Verify embed content
        embed = ctx.send.call_args[0][0]
        self.assertIsInstance(embed, discord.Embed)
        self.assertIn('SPY', embed.title)
        self.assertIn('475.25', embed.description)
        self.assertIn('BULLISH', embed.description)

    @pytest.mark.asyncio
    async def test_stats_command(self):
        """Test !tbow stats command"""
        ctx = AsyncMock()
        ctx.send = AsyncMock()
        
        await self.bot.tbow(ctx, 'stats')
        
        # Verify command processing
        self.tactics.get_stats.assert_called_once()
        ctx.send.assert_called_once()
        
        # Verify embed content
        embed = ctx.send.call_args[0][0]
        self.assertIsInstance(embed, discord.Embed)
        self.assertIn('65.0%', embed.description)
        self.assertIn('2.1:1', embed.description)

    @pytest.mark.asyncio
    async def test_alert_command(self):
        """Test !tbow alert command"""
        ctx = AsyncMock()
        ctx.send = AsyncMock()
        ctx.author.id = 123456789
        
        await self.bot.tbow(ctx, 'alert', 'TSLA', 'MACD_curl_up', '&&', 'RSI_below_40')
        
        # Verify alert creation
        ctx.send.assert_called_once()
        self.assertIn('Alert set', ctx.send.call_args[0][0])
        self.assertIn('Alert ID:', ctx.send.call_args[0][0])
        self.assertIn('MACD_curl_up && RSI_below_40', ctx.send.call_args[0][0])
        
        # Verify alert storage
        with open(self.alert_file, 'r') as f:
            alerts = json.load(f)
            self.assertEqual(len(alerts), 1)
            self.assertEqual(alerts[0]['symbol'], 'TSLA')
            self.assertEqual(alerts[0]['conditions'], ["MACD_curl_up", "RSI_below_40"])
            self.assertIn('alert_id', alerts[0])
            self.assertEqual(alerts[0]['cooldown_seconds'], 300)

    @pytest.mark.asyncio
    async def test_alert_delete_command(self):
        """Test !tbow alert delete command"""
        # Create test alert
        alert = AlertRule(
            symbol='TSLA',
            conditions=['MACD_curl_up', 'RSI_below_40'],
            target='123456789',
            user_id='123456789',
            created=datetime.now()
        )
        self.bot.alert_manager.add_rule(alert)
        
        ctx = AsyncMock()
        ctx.send = AsyncMock()
        
        await self.bot.tbow(ctx, 'alert', 'delete', alert.alert_id)
        
        # Verify alert deletion
        ctx.send.assert_called_once()
        self.assertIn('deleted', ctx.send.call_args[0][0])
        
        # Verify alert removed from storage
        with open(self.alert_file, 'r') as f:
            alerts = json.load(f)
            self.assertEqual(len(alerts), 0)

    @pytest.mark.asyncio
    async def test_alert_modify_command(self):
        """Test !tbow alert modify command"""
        # Create test alert
        alert = AlertRule(
            symbol='TSLA',
            conditions=['MACD_curl_up', 'RSI_below_40'],
            target='123456789',
            user_id='123456789',
            created=datetime.now()
        )
        self.bot.alert_manager.add_rule(alert)
        
        ctx = AsyncMock()
        ctx.send = AsyncMock()
        
        await self.bot.tbow(ctx, 'alert', 'modify', alert.alert_id, 'cooldown', '600')
        
        # Verify alert modification
        ctx.send.assert_called_once()
        self.assertIn('modified', ctx.send.call_args[0][0])
        
        # Verify alert updated in storage
        with open(self.alert_file, 'r') as f:
            alerts = json.load(f)
            self.assertEqual(len(alerts), 1)
            self.assertEqual(alerts[0]['cooldown_seconds'], 600)

    @pytest.mark.asyncio
    async def test_alerts_command(self):
        """Test !tbow alerts command"""
        # Create test alerts
        alert = AlertRule(
            symbol='TSLA',
            conditions=['MACD_curl_up', 'RSI_below_40'],
            target='123456789',
            user_id='123456789',
            created=datetime.now(),
            last_triggered=datetime.now()
        )
        self.bot.alert_manager.add_rule(alert)
        
        ctx = AsyncMock()
        ctx.send = AsyncMock()
        ctx.author.id = 123456789
        
        await self.bot.tbow(ctx, 'alerts')
        
        # Verify alert listing
        ctx.send.assert_called_once()
        embed = ctx.send.call_args[0][0]
        self.assertIsInstance(embed, discord.Embed)
        self.assertIn('Your Alerts', embed.title)
        self.assertIn(alert.alert_id, embed.fields[0].value)
        self.assertIn('MACD_curl_up && RSI_below_40', embed.fields[0].value)
        self.assertIn('Cooldown: 300s', embed.fields[0].value)

    @pytest.mark.asyncio
    async def test_alert_trigger(self):
        """Test alert triggering"""
        # Create test alert
        alert = AlertRule(
            symbol='TSLA',
            conditions=['MACD_curl_up', 'RSI_below_40'],
            target='123456789',
            user_id='123456789',
            created=datetime.now()
        )
        self.bot.alert_manager.add_rule(alert)
        
        # Mock market data
        self.tactics.get_status = Mock(return_value={
            'price': 215.50,
            'change': 1.2,
            'macd': 'BULLISH',
            'macd_curl': True,
            'rsi': 35
        })
        
        # Mock channel
        channel = AsyncMock()
        channel.send = AsyncMock()
        self.bot.get_channel = Mock(return_value=channel)
        
        # Trigger alert check
        await self.bot.alert_manager.check_alerts()
        
        # Verify alert trigger
        channel.send.assert_called_once()
        self.assertIn('Alert: TSLA', channel.send.call_args[0][0])
        self.assertIn('MACD_curl_up', channel.send.call_args[0][1].fields[1].value)
        self.assertIn('RSI_below_40', channel.send.call_args[0][1].fields[1].value)
        
        # Verify last triggered time updated
        with open(self.alert_file, 'r') as f:
            alerts = json.load(f)
            self.assertEqual(len(alerts), 1)
            self.assertIn('last_triggered', alerts[0])
        
        # Verify alert logged
        with open(self.alert_log, 'r') as f:
            lines = f.readlines()
            self.assertEqual(len(lines), 2)  # Header + 1 alert
            self.assertIn('TSLA', lines[1])
            self.assertIn('MACD_curl_up && RSI_below_40', lines[1])

    @pytest.mark.asyncio
    async def test_alert_cooldown(self):
        """Test alert cooldown functionality"""
        # Create test alert
        alert = AlertRule(
            symbol='TSLA',
            conditions=['MACD_curl_up', 'RSI_below_40'],
            target='123456789',
            user_id='123456789',
            created=datetime.now(),
            last_triggered=datetime.now(),
            cooldown_seconds=300
        )
        self.bot.alert_manager.add_rule(alert)
        
        # Mock market data
        self.tactics.get_status = Mock(return_value={
            'price': 215.50,
            'change': 1.2,
            'macd': 'BULLISH',
            'macd_curl': True,
            'rsi': 35
        })
        
        # Mock channel
        channel = AsyncMock()
        channel.send = AsyncMock()
        self.bot.get_channel = Mock(return_value=channel)
        
        # Trigger alert check (should be blocked by cooldown)
        await self.bot.alert_manager.check_alerts()
        
        # Verify alert not triggered
        channel.send.assert_not_called()
        
        # Update last triggered time to be older than cooldown
        alert.last_triggered = datetime.now() - timedelta(seconds=301)
        self.bot.alert_manager._save_rules()
        
        # Trigger alert check again (should work now)
        await self.bot.alert_manager.check_alerts()
        
        # Verify alert triggered
        channel.send.assert_called_once()

    @pytest.mark.asyncio
    async def test_role_mention(self):
        """Test role-based mentions"""
        # Set role ID in environment
        os.environ['ALERT_MENTION_ROLE_ID'] = '987654321'
        
        # Create test alert
        alert = AlertRule(
            symbol='TSLA',
            conditions=['MACD_curl_up', 'RSI_below_40'],
            target='123456789',
            user_id='123456789',
            created=datetime.now()
        )
        self.bot.alert_manager.add_rule(alert)
        
        # Mock market data
        self.tactics.get_status = Mock(return_value={
            'price': 215.50,
            'change': 1.2,
            'macd': 'BULLISH',
            'macd_curl': True,
            'rsi': 35
        })
        
        # Mock channel
        channel = AsyncMock()
        channel.send = AsyncMock()
        self.bot.get_channel = Mock(return_value=channel)
        
        # Trigger alert check
        await self.bot.alert_manager.check_alerts()
        
        # Verify role mention
        channel.send.assert_called_once()
        self.assertIn('<@&987654321>', channel.send.call_args[0][0])
        
        # Clean up
        del os.environ['ALERT_MENTION_ROLE_ID']

    def test_price_cache(self):
        """Test price cache functionality"""
        cache = PriceCache()
        now = datetime.now()
        
        # Update cache
        cache.update('TSLA', 215.50, now)
        cache.update('TSLA', 216.00, now + timedelta(minutes=5))
        cache.update('TSLA', 216.50, now + timedelta(minutes=10))
        
        # Test price lookup
        price = cache.get_price_after('TSLA', now, minutes=30)
        self.assertIsNone(price)  # No price after 30 minutes
        
        price = cache.get_price_after('TSLA', now, minutes=5)
        self.assertEqual(price, 216.00)
        
        # Test non-existent symbol
        price = cache.get_price_after('AAPL', now)
        self.assertIsNone(price)

    def test_alert_logger(self):
        """Test alert logger functionality"""
        logger = AlertLogger(self.alert_log)
        
        # Create test alert
        alert = AlertRule(
            symbol='TSLA',
            conditions=['MACD_curl_up', 'RSI_below_40'],
            target='123456789',
            user_id='123456789',
            created=datetime.now()
        )
        
        # Log alert
        logger.log_alert(alert, 215.50, 216.00)
        
        # Verify log file
        with open(self.alert_log, 'r') as f:
            lines = f.readlines()
            self.assertEqual(len(lines), 2)  # Header + 1 alert
            self.assertIn('TSLA', lines[1])
            self.assertIn('MACD_curl_up && RSI_below_40', lines[1])
            self.assertIn('215.50', lines[1])
            self.assertIn('216.00', lines[1])
        
        # Test get_todays_alerts
        alerts = logger.get_todays_alerts()
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0]['symbol'], 'TSLA')
        self.assertEqual(alerts[0]['price_at_fire'], 215.50)
        self.assertEqual(alerts[0]['price_after_30m'], 216.00)

    @pytest.mark.asyncio
    async def test_digest_command(self):
        """Test !tbow digest command"""
        # Create test alerts
        alert = AlertRule(
            symbol='TSLA',
            conditions=['MACD_curl_up', 'RSI_below_40'],
            target='123456789',
            user_id='123456789',
            created=datetime.now()
        )
        self.bot.alert_manager.add_rule(alert)
        
        # Log some alerts
        self.bot.digest_manager.alert_logger.log_alert(alert, 215.50, 216.00)
        self.bot.digest_manager.alert_logger.log_alert(alert, 216.00, 216.50)
        self.bot.digest_manager.alert_logger.log_alert(alert, 216.50, 217.00)
        
        ctx = AsyncMock()
        ctx.send = AsyncMock()
        ctx.channel.id = 123456789
        
        await self.bot.tbow(ctx, 'digest', 'today')
        
        # Verify digest generation
        ctx.send.assert_called_once()
        embed = ctx.send.call_args[0][0]
        self.assertIsInstance(embed, discord.Embed)
        self.assertIn('Daily Alert Digest', embed.title)
        self.assertIn('TSLA', embed.fields[0].name)
        self.assertIn('Fires: 3', embed.fields[0].value)
        self.assertIn('215.50 → 217.00', embed.fields[0].value)
        
        # Verify digest saved
        digest_file = os.path.join('runtime/digests', f"{datetime.now().strftime('%Y-%m-%d')}.json")
        self.assertTrue(os.path.exists(digest_file))

    @pytest.mark.asyncio
    async def test_digest_schedule(self):
        """Test digest scheduling"""
        # Mock current time to 21:00 ET
        with patch('datetime.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2024, 1, 20, 21, 0, 0)
            
            # Create test alerts
            alert = AlertRule(
                symbol='TSLA',
                conditions=['MACD_curl_up', 'RSI_below_40'],
                target='123456789',
                user_id='123456789',
                created=datetime.now()
            )
            self.bot.alert_manager.add_rule(alert)
            
            # Log some alerts
            self.bot.digest_manager.alert_logger.log_alert(alert, 215.50, 216.00)
            
            # Mock channel
            channel = AsyncMock()
            channel.send = AsyncMock()
            self.bot.get_channel = Mock(return_value=channel)
            
            # Check schedule
            await self.bot.digest_manager.check_digest_schedule()
            
            # Verify digest sent
            channel.send.assert_called_once()
            self.assertIn('Daily Alert Digest', channel.send.call_args[0][0])

if __name__ == '__main__':
    unittest.main() 