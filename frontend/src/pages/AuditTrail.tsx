import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import Box from '@mui/material/Box';
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import Typography from '@mui/material/Typography';
import Grid from '@mui/material/Grid';
import TextField from '@mui/material/TextField';
import MenuItem from '@mui/material/MenuItem';
import Button from '@mui/material/Button';
import Table from '@mui/material/Table';
import TableBody from '@mui/material/TableBody';
import TableCell from '@mui/material/TableCell';
import TableContainer from '@mui/material/TableContainer';
import TableHead from '@mui/material/TableHead';
import TableRow from '@mui/material/TableRow';
import Paper from '@mui/material/Paper';
import TablePagination from '@mui/material/TablePagination';
import IconButton from '@mui/material/IconButton';
import SearchIcon from '@mui/icons-material/Search';
import ClearIcon from '@mui/icons-material/Clear';
import Link from '@mui/material/Link';
import Alert from '@mui/material/Alert';
import CircularProgress from '@mui/material/CircularProgress';
import Chip from '@mui/material/Chip';
import type { ReviewAction } from '../types';
import { getAuditTrail } from '../api/client';

const AuditTrail: React.FC = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  // Audit logs state
  const [logs, setLogs] = useState<any[]>([]);
  const [totalCount, setTotalCount] = useState(0);
  
  // Pagination state
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(25);
  
  // Filters state
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedAction, setSelectedAction] = useState('');
  const [selectedEntityType, setSelectedEntityType] = useState('');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');

  const fetchAuditLogs = () => {
    setLoading(true);
    setError(null);

    const params: Record<string, any> = {
      page: page + 1, // API is 1-indexed
      page_size: rowsPerPage,
    };

    if (searchTerm) params.search = searchTerm;
    if (selectedAction) params.action = selectedAction;
    if (selectedEntityType) params.entity_type = selectedEntityType;
    if (startDate) params.start_date = startDate;
    if (endDate) params.end_date = endDate;

    getAuditTrail(params)
      .then((res: any) => {
        if (res && 'results' in res) {
          setLogs(res.results);
          setTotalCount(res.count);
        } else {
          const arr = res as any[];
          setLogs(arr);
          setTotalCount(arr.length);
        }
        setLoading(false);
      })
      .catch((err: any) => {
        setError(err.message || 'Failed to fetch audit log trail.');
        setLoading(false);
      });
  };

  useEffect(() => {
    fetchAuditLogs();
  }, [page, rowsPerPage, selectedAction, selectedEntityType, startDate, endDate]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(0);
    fetchAuditLogs();
  };

  const clearFilters = () => {
    setSearchTerm('');
    setSelectedAction('');
    setSelectedEntityType('');
    setStartDate('');
    setEndDate('');
    setPage(0);
  };

  return (
    <Box>
      <Typography variant="h4" gutterBottom sx={{ mb: 4, fontWeight: 700 }}>
        Immutable Audit & Mutation Trail
      </Typography>

      <Typography variant="body2" color="text.secondary" sx={{ mb: 4 }}>
        This ledger records every database state change, import transaction, and analyst workflow action. 
        It provides third-party financial auditors with an append-only, chronologically sorted timeline of data custody.
      </Typography>

      {/* Filters Card */}
      <Card sx={{ mb: 4 }}>
        <CardContent sx={{ p: 3 }}>
          <Box component="form" onSubmit={handleSearchSubmit}>
            <Grid container spacing={3} alignItems="center">
              {/* Search */}
              <Grid item xs={12} md={3}>
                <TextField
                  fullWidth
                  label="Search performed by"
                  placeholder="Analyst name, IP..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  InputProps={{
                    startAdornment: <SearchIcon color="action" sx={{ mr: 1 }} />,
                  }}
                />
              </Grid>

              {/* Action type */}
              <Grid item xs={12} sm={6} md={2.5}>
                <TextField
                  select
                  fullWidth
                  label="Action Type"
                  value={selectedAction}
                  onChange={(e) => {
                    setSelectedAction(e.target.value);
                    setPage(0);
                  }}
                >
                  <MenuItem value="">All Actions</MenuItem>
                  <MenuItem value="create">CREATE (Ingest)</MenuItem>
                  <MenuItem value="update">UPDATE (Review/Edit)</MenuItem>
                  <MenuItem value="delete">DELETE (Clear)</MenuItem>
                </TextField>
              </Grid>

              {/* Entity Type */}
              <Grid item xs={12} sm={6} md={2.5}>
                <TextField
                  select
                  fullWidth
                  label="Entity Type"
                  value={selectedEntityType}
                  onChange={(e) => {
                    setSelectedEntityType(e.target.value);
                    setPage(0);
                  }}
                >
                  <MenuItem value="">All Entities</MenuItem>
                  <MenuItem value="EmissionRecord">EmissionRecord (Workflows)</MenuItem>
                  <MenuItem value="RawRecord">RawRecord (Inputs)</MenuItem>
                  <MenuItem value="DataSource">DataSource (Config)</MenuItem>
                </TextField>
              </Grid>

              {/* Start Date */}
              <Grid item xs={12} sm={6} md={2}>
                <TextField
                  fullWidth
                  type="date"
                  label="Mutated Date From"
                  InputLabelProps={{ shrink: true }}
                  value={startDate}
                  onChange={(e) => setStartDate(e.target.value)}
                />
              </Grid>

              {/* End Date */}
              <Grid item xs={12} sm={6} md={2}>
                <TextField
                  fullWidth
                  type="date"
                  label="Mutated Date To"
                  InputLabelProps={{ shrink: true }}
                  value={endDate}
                  onChange={(e) => setEndDate(e.target.value)}
                />
              </Grid>

              {/* Actions */}
              <Grid item xs={12} md={12} sx={{ display: 'flex', justifyContent: 'flex-end', gap: 1, mt: 1 }}>
                <IconButton onClick={clearFilters} color="secondary" title="Clear filters">
                  <ClearIcon />
                </IconButton>
                <Button type="submit" variant="contained" color="primary" sx={{ fontWeight: 600, px: 4 }}>
                  Filter Trail
                </Button>
              </Grid>
            </Grid>
          </Box>
        </CardContent>
      </Card>

      {/* Main Table */}
      <TableContainer component={Paper} sx={{ border: '1px solid #E0E0E0', boxShadow: 'none' }}>
        {loading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}>
            <CircularProgress />
          </Box>
        ) : (
          <>
            <Table size="medium">
              <TableHead>
                <TableRow>
                  <TableCell sx={{ fontWeight: 600, width: '8%' }}>ID</TableCell>
                  <TableCell sx={{ fontWeight: 600 }}>Timestamp</TableCell>
                  <TableCell sx={{ fontWeight: 600 }}>Entity Type</TableCell>
                  <TableCell sx={{ fontWeight: 600 }}>Entity Link ID</TableCell>
                  <TableCell sx={{ fontWeight: 600 }}>Action</TableCell>
                  <TableCell sx={{ fontWeight: 600 }}>Performed By</TableCell>
                  <TableCell sx={{ fontWeight: 600 }}>Source IP</TableCell>
                  <TableCell sx={{ fontWeight: 600 }}>Mutation Detail (JSON Diffs)</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {logs.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={8} align="center" sx={{ py: 6, color: 'text.secondary' }}>
                      No audit trails logged yet.
                    </TableCell>
                  </TableRow>
                ) : (
                  logs.map((log) => {
                    const isEmission = log.entity_type === 'EmissionRecord';
                    const hasStatus = log.changes && log.changes.status;
                    const statusDiff = hasStatus ? `${log.changes.status.from} → ${log.changes.status.to}` : '';
                    
                    return (
                      <TableRow key={log.id} hover>
                        <TableCell sx={{ fontFamily: 'monospace', color: 'text.secondary' }}>
                          #{log.id}
                        </TableCell>
                        <TableCell>
                          {new Date(log.created_at).toLocaleString()}
                        </TableCell>
                        <TableCell sx={{ fontWeight: 600 }}>
                          {log.entity_type}
                        </TableCell>
                        <TableCell>
                          {isEmission ? (
                            <Link 
                              onClick={() => navigate(`/records/${log.entity_id}`)} 
                              sx={{ cursor: 'pointer', fontWeight: 600, fontFamily: 'monospace' }}
                            >
                              {log.entity_id.substring(0, 8)}...
                            </Link>
                          ) : (
                            <span style={{ fontFamily: 'monospace' }}>{log.entity_id.substring(0, 8)}...</span>
                          )}
                        </TableCell>
                        <TableCell>
                          <Chip
                            label={log.action.toUpperCase()}
                            size="small"
                            color={log.action === 'create' ? 'success' : log.action === 'delete' ? 'error' : 'primary'}
                            sx={{ fontWeight: 700, fontSize: '0.7rem' }}
                          />
                        </TableCell>
                        <TableCell sx={{ fontWeight: 600 }}>
                          {log.performed_by}
                        </TableCell>
                        <TableCell sx={{ fontFamily: 'monospace', fontSize: '0.85rem' }}>
                          {log.ip_address || '-'}
                        </TableCell>
                        <TableCell sx={{ maxWidth: 300, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                          <span style={{ fontSize: '0.85rem', fontFamily: 'monospace', color: '#1B5E20' }}>
                            {statusDiff ? `Status: ${statusDiff}` : JSON.stringify(log.changes)}
                          </span>
                        </TableCell>
                      </TableRow>
                    );
                  })
                )}
              </TableBody>
            </Table>
            
            <TablePagination
              component="div"
              count={totalCount}
              rowsPerPage={rowsPerPage}
              page={page}
              onPageChange={(_, newPage) => setPage(newPage)}
              onRowsPerPageChange={(e) => {
                setRowsPerPage(parseInt(e.target.value, 10));
                setPage(0);
              }}
              rowsPerPageOptions={[10, 25, 50, 100]}
            />
          </>
        )}
      </TableContainer>
    </Box>
  );
};

export default AuditTrail;
