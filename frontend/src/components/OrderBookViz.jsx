import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine,
} from 'recharts';

export default function OrderBookViz({ params }) {
  const [bookData, setBookData] = useState([]);
  const [midPrice, setMidPrice] = useState(100);

  useEffect(() => {
    // Generate synthetic order book display
    const mid = 100;
    setMidPrice(mid);
    const levels = [];
    for (let i = 10; i >= 1; i--) {
      const price = mid + i * 0.01;
      const depth = Math.round(500 + Math.random() * 2000);
      levels.push({
        price: price.toFixed(2),
        ask: depth,
        bid: 0,
        side: 'ask',
      });
    }
    for (let i = 1; i <= 10; i++) {
      const price = mid - i * 0.01;
      const depth = Math.round(500 + Math.random() * 2000);
      levels.push({
        price: price.toFixed(2),
        ask: 0,
        bid: -depth,
        side: 'bid',
      });
    }
    setBookData(levels);
  }, [params]);

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-bg-card border border-border rounded-xl p-5"
    >
      <h3 className="text-sm font-medium text-text-secondary mb-4">Order Book Depth</h3>
      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={bookData} layout="horizontal">
            <CartesianGrid strokeDasharray="3 3" stroke="#1A2535" />
            <XAxis dataKey="price" stroke="#8B9CB6" fontSize={9} interval={1} />
            <YAxis stroke="#8B9CB6" fontSize={11} />
            <Tooltip
              contentStyle={{
                backgroundColor: '#0D1320',
                border: '1px solid #1A2535',
                borderRadius: '8px',
                color: '#E8ECF0',
                fontSize: 12,
              }}
              formatter={(value) => [Math.abs(value), 'Depth (shares)']}
            />
            <ReferenceLine x={midPrice.toFixed(2)} stroke="#C9A84C" strokeDasharray="5 5" label="" />
            <Bar dataKey="ask" fill="#4C7AE0" opacity={0.7} />
            <Bar dataKey="bid" fill="#C9A84C" opacity={0.7} />
          </BarChart>
        </ResponsiveContainer>
      </div>
      <div className="flex justify-between text-xs text-text-secondary mt-2">
        <span className="text-accent-gold">Bid (left)</span>
        <span>Mid: ${midPrice.toFixed(2)}</span>
        <span className="text-accent-info">Ask (right)</span>
      </div>
    </motion.div>
  );
}
