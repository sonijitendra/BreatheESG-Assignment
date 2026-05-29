import React from 'react';
import Chip from '@mui/material/Chip';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import HourglassEmptyIcon from '@mui/icons-material/HourglassEmpty';
import FlagIcon from '@mui/icons-material/Flag';
import RateReviewIcon from '@mui/icons-material/RateReview';
import CancelIcon from '@mui/icons-material/Cancel';
import LockIcon from '@mui/icons-material/Lock';
import { useTheme } from '@mui/material/styles';

interface StatusChipProps {
  status: string;
  size?: 'small' | 'medium';
}

const statusConfig: Record<
  string,
  { label: string; icon: React.ReactElement; colorKey: string }
> = {
  pending: {
    label: 'Pending',
    icon: <HourglassEmptyIcon fontSize="small" />,
    colorKey: 'pending',
  },
  flagged: {
    label: 'Flagged',
    icon: <FlagIcon fontSize="small" />,
    colorKey: 'flagged',
  },
  reviewed: {
    label: 'Reviewed',
    icon: <RateReviewIcon fontSize="small" />,
    colorKey: 'reviewed',
  },
  approved: {
    label: 'Approved',
    icon: <CheckCircleIcon fontSize="small" />,
    colorKey: 'approved',
  },
  rejected: {
    label: 'Rejected',
    icon: <CancelIcon fontSize="small" />,
    colorKey: 'rejected',
  },
  locked: {
    label: 'Locked',
    icon: <LockIcon fontSize="small" />,
    colorKey: 'locked',
  },
};

const StatusChip: React.FC<StatusChipProps> = ({ status, size = 'small' }) => {
  const theme = useTheme();
  const config = statusConfig[status] || {
    label: status,
    icon: <HourglassEmptyIcon fontSize="small" />,
    colorKey: 'pending',
  };
  const color =
    theme.palette.status[config.colorKey as keyof typeof theme.palette.status] ||
    '#757575';

  return (
    <Chip
      icon={config.icon}
      label={config.label}
      size={size}
      sx={{
        backgroundColor: `${color}18`,
        color: color,
        borderColor: `${color}40`,
        border: '1px solid',
        fontWeight: 600,
        '& .MuiChip-icon': {
          color: color,
        },
      }}
    />
  );
};

export default StatusChip;
