class SparklineReporter:
    def __init__(self):
        # Unicode block elements from lowest (1/8) to full (8/8)
        self.spark_chars = [' ', '▂', '▃', '▄', '▅', '▆', '▇', '█']
    
    def generate_sparkline(self, data_series):
        if not data_series or len(data_series) < 2:
            return ""

        min_val = min(data_series)
        max_val = max(data_series)
        val_range = max_val - min_val

        if val_range == 0:
            return self.spark_chars[3] * len(data_series) 

        sparkline = []
        for x in data_series:
            # Normalize 0-1
            normalized = (x - min_val) / val_range
            # Map to index 0-7
            char_index = int(normalized * (len(self.spark_chars) - 1))
            sparkline.append(self.spark_chars[char_index])

        return "".join(sparkline)

    def generate_sequence_list(self, opens, closes, doji_threshold_pct=0.05):
        """
        Returns a list like ["UP", "DOWN", "DOJI"]
        """
        sequence_list = []
        for o, c in zip(opens, closes):
            body_size_pct = abs(c - o) / o * 100
            
            if body_size_pct < doji_threshold_pct:
                sequence_list.append("DOJI")
            elif c > o:
                sequence_list.append("UP")
            else:
                sequence_list.append("DOWN")
                
        return sequence_list

    def create_report(self, candles, period=14, generate_sequence=True, sparkline_mode='both'):
        """
        sparkline_mode options: 'price', 'volume', 'both'
        """
        # 1. Slice data
        recent_data = candles[-period:]
        
        # Prepare result dictionary
        result_visuals = {
            "period_bars": len(recent_data),
            "authority": "context_only"
        }

        # --- PRICE BLOCK (Includes Sparkline & Sequence) ---
        # Only run if mode is 'price' or 'both'
        if sparkline_mode in ['price', 'both']:
            closes = [c['close'] for c in recent_data]
            result_visuals['price_sparkline'] = self.generate_sparkline(closes)
            
            # Sequence is price-based, so it lives inside this block
            if generate_sequence:
                opens = [c['open'] for c in recent_data]
                sequence_list = self.generate_sequence_list(opens, closes)
                result_visuals['sequence'] = sequence_list
                # Calculate ratio safely
                if sequence_list:
                    result_visuals['doji_ratio'] = round(sequence_list.count("DOJI") / len(sequence_list), 2)
                else:
                    result_visuals['doji_ratio'] = 0

        # --- VOLUME BLOCK ---
        # Only run if mode is 'volume' or 'both'
        if sparkline_mode in ['volume', 'both']:
            volumes = [c.get('volume', 0) for c in recent_data]
            result_visuals['volume_sparkline'] = self.generate_sparkline(volumes)

        return {
            "visuals": result_visuals
        }

