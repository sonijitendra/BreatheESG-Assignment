import React from 'react';
import Chip from '@mui/material/Chip';

interface ScopeChipProps {
  scope: number;
  size?: 'small' | 'medium';
}

const scopeColors: Record<number, string> = {
  1: '#E65100',
  2: '#1565C0',
  3: '#6A1B9A',
};

const ScopeChip: React.FC<ScopeChipProps> = ({ scope, size = 'small' }) => {
  const color = scopeColors[scope] || '#757575';
  return (
    <Chip
      label={`Scope ${scope}`}
      size={size}
      sx={{
        backgroundColor: `${color}14`,
        color: color,
        fontWeight: 700,
        fontSize: '0.75rem',
        border: `1px solid ${color}40`,
      }}
    />
  );
};

export default ScopeChip;
