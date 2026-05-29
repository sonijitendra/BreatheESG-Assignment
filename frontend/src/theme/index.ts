import { createTheme } from '@mui/material/styles';

declare module '@mui/material/styles' {
  interface Palette {
    status: {
      pending: string;
      flagged: string;
      reviewed: string;
      approved: string;
      rejected: string;
      locked: string;
    };
    scope: {
      scope1: string;
      scope2: string;
      scope3: string;
    };
  }
  interface PaletteOptions {
    status?: {
      pending: string;
      flagged: string;
      reviewed: string;
      approved: string;
      rejected: string;
      locked: string;
    };
    scope?: {
      scope1: string;
      scope2: string;
      scope3: string;
    };
  }
}

const theme = createTheme({
  palette: {
    primary: {
      main: '#00695C',
      light: '#439889',
      dark: '#003D33',
      contrastText: '#FFFFFF',
    },
    secondary: {
      main: '#546E7A',
      light: '#819CA9',
      dark: '#29434E',
      contrastText: '#FFFFFF',
    },
    background: {
      default: '#F5F7FA',
      paper: '#FFFFFF',
    },
    status: {
      pending: '#F57C00',
      flagged: '#D32F2F',
      reviewed: '#1976D2',
      approved: '#2E7D32',
      rejected: '#C2185B',
      locked: '#757575',
    },
    scope: {
      scope1: '#E65100',
      scope2: '#1565C0',
      scope3: '#6A1B9A',
    },
  },
  typography: {
    fontFamily: '"Inter", "Roboto", "Helvetica", "Arial", sans-serif',
    h4: {
      fontWeight: 700,
      fontSize: '1.75rem',
    },
    h5: {
      fontWeight: 600,
      fontSize: '1.35rem',
    },
    h6: {
      fontWeight: 600,
      fontSize: '1.1rem',
    },
    subtitle1: {
      fontWeight: 500,
    },
    body2: {
      color: '#616161',
    },
  },
  shape: {
    borderRadius: 8,
  },
  components: {
    MuiCard: {
      styleOverrides: {
        root: {
          boxShadow: '0 1px 3px rgba(0,0,0,0.08), 0 1px 2px rgba(0,0,0,0.06)',
          border: '1px solid #E0E0E0',
        },
      },
    },
    MuiButton: {
      styleOverrides: {
        root: {
          textTransform: 'none',
          fontWeight: 600,
        },
      },
    },
    MuiChip: {
      styleOverrides: {
        root: {
          fontWeight: 500,
        },
      },
    },
    MuiAppBar: {
      styleOverrides: {
        root: {
          boxShadow: '0 1px 3px rgba(0,0,0,0.08)',
        },
      },
    },
    MuiDrawer: {
      styleOverrides: {
        paper: {
          borderRight: '1px solid #E0E0E0',
        },
      },
    },
  },
});

export default theme;
