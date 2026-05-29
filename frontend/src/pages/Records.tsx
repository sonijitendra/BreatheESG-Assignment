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
import FormGroup from '@mui/material/FormGroup';
import FormControlLabel from '@mui/material/FormControlLabel';
import Checkbox from '@mui/material/Checkbox';
import Table from '@mui/material/Table';
import TableBody from '@mui/material/TableBody';
import TableCell from '@mui/material/TableCell';
import TableContainer from '@mui/material/TableContainer';
import TableHead from '@mui/material/TableHead';
import TableRow from '@mui/material/TableRow';
import Paper from '@mui/material/Paper';
import TablePagination from '@mui/material/TablePagination';
import IconButton from '@mui/material/IconButton';
import InputAdornment from '@mui/material/InputAdornment';
import SearchIcon from '@mui/icons-material/Search';
import WarningIcon from '@mui/icons-material/Warning';
import VisibilityIcon from '@mui/icons-material/Visibility';
import FactCheckIcon from '@mui/icons-material/FactCheck';
import CheckCircleOutlineIcon from '@mui/icons-material/CheckCircleOutline';
import ClearIcon from '@mui/icons-material/Clear';
import Tooltip from '@mui/material/Tooltip';
import Alert from '@mui/material/Alert';
import CircularProgress from '@mui/material/CircularProgress';
import type { EmissionRecord, RecordFilters } from '../types';
import { getEmissionRecords, bulkReview } from '../api/client';
import StatusChip from '../components/StatusChip';
import ScopeChip from '../components/ScopeChip';

const scopes = [1, 2, 3];
const statuses = ['pending', 'flagged', 'reviewed', 'approved', 'rejected', 'locked'];
const sources = [
  { value: 'sap', label: 'SAP Fuel Procurement' },
  { value: 'utility', label: 'Utility Electricity' },
  { value: 'travel', label: 'Corporate Travel' },
];

const Records: React.FC = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  // Records state
  const [records, setRecords] = useState<EmissionRecord[]>([]);
  const [totalCount, setTotalCount] = useState(0);
  
  // Pagination state
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(25);
  
  // Filters state
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedScopes, setSelectedScopes] = useState<number[]>([]);
  const [selectedStatuses, setSelectedStatuses] = useState<string[]>([]);
  const [selectedSources, setSelectedSources] = useState<string[]>([]);
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');

  // Row selection
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  
  // Bulk action execution
  const [bulkProcessing, setBulkProcessing] = useState(false);
  const [bulkMsg, setBulkMsg] = useState<{ type: 'success' | 'error', text: string } | null>(null);

  const fetchRecords = () => {
    setLoading(true);
    setError(null);
    
    const filters: RecordFilters & { page: number, page_size: number, search?: string, start_date?: string, end_date?: string } = {
      page: page + 1, // API is 1-indexed
      page_size: rowsPerPage,
      scope: selectedScopes,
      status: selectedStatuses,
      source_type: selectedSources,
    };
    
    if (searchTerm) filters.search = searchTerm;
    if (startDate) filters.start_date = startDate;
    if (endDate) filters.end_date = endDate;

    getEmissionRecords(filters)
      .then((res) => {
        // If the API returns paginated data (count + results)
        if (res && 'results' in res) {
          setRecords(res.results);
          setTotalCount(res.count);
        } else {
          // If fallback returns simple array
          const arr = res as unknown as EmissionRecord[];
          setRecords(arr);
          setTotalCount(arr.length);
        }
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message || 'Failed to fetch emission records.');
        setLoading(false);
      });
  };

  useEffect(() => {
    fetchRecords();
  }, [page, rowsPerPage, selectedScopes, selectedStatuses, selectedSources, startDate, endDate]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(0);
    fetchRecords();
  };

  const clearFilters = () => {
    setSearchTerm('');
    setSelectedScopes([]);
    setSelectedStatuses([]);
    setSelectedSources([]);
    setStartDate('');
    setEndDate('');
    setPage(0);
  };

  // Row checkbox selection handlers
  const handleSelectAll = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.checked) {
      const ids = records.map(r => r.id);
      setSelectedIds(ids);
    } else {
      setSelectedIds([]);
    }
  };

  const handleSelectOne = (id: string) => {
    const idx = selectedIds.indexOf(id);
    if (idx === -1) {
      setSelectedIds([...selectedIds, id]);
    } else {
      setSelectedIds(selectedIds.filter(item => item !== id));
    }
  };

  // Bulk workflow approvals
  const handleBulkAction = (actionName: 'review' | 'approve') => {
    if (selectedIds.length === 0) return;
    
    setBulkProcessing(true);
    setBulkMsg(null);
    
    bulkReview(selectedIds, actionName, 'system_analyst', `Bulk ${actionName} applied via records list.`)
      .then((res) => {
        setBulkProcessing(false);
        setSelectedIds([]);
        setBulkMsg({
          type: 'success',
          text: `Successfully updated ${res.successful_count} records. ${res.failed_count} records failed state check.`
        });
        fetchRecords(); // Refresh list
      })
      .catch((err) => {
        setBulkProcessing(false);
        setBulkMsg({
          type: 'error',
          text: err.message || `Bulk ${actionName} execution failed.`
        });
      });
  };

  return (
    <Box>
      <Typography variant="h4" gutterBottom sx={{ mb: 4, fontWeight: 700 }}>
        Analytical Emission Ledger
      </Typography>

      {/* Dynamic Filters Workspace */}
      <Card sx={{ mb: 4 }}>
        <CardContent sx={{ p: 3 }}>
          <Box component="form" onSubmit={handleSearchSubmit}>
            <Grid container spacing={3} alignItems="center">
              {/* Keyword Search */}
              <Grid item xs={12} md={4}>
                <TextField
                  fullWidth
                  label="Search ledger"
                  placeholder="Material, Vendor, Description..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  InputProps={{
                    startAdornment: (
                      <InputAdornment position="start">
                        <SearchIcon />
                      </InputAdornment>
                    ),
                  }}
                />
              </Grid>

              {/* Start Date */}
              <Grid item xs={12} sm={6} md={3}>
                <TextField
                  fullWidth
                  type="date"
                  label="Activity Date From"
                  InputLabelProps={{ shrink: true }}
                  value={startDate}
                  onChange={(e) => setStartDate(e.target.value)}
                />
              </Grid>

              {/* End Date */}
              <Grid item xs={12} sm={6} md={3}>
                <TextField
                  fullWidth
                  type="date"
                  label="Activity Date To"
                  InputLabelProps={{ shrink: true }}
                  value={endDate}
                  onChange={(e) => setEndDate(e.target.value)}
                />
              </Grid>

              {/* Submit / Clear */}
              <Grid item xs={12} md={2} sx={{ display: 'flex', gap: 1 }}>
                <Button type="submit" variant="contained" color="primary" fullWidth sx={{ fontWeight: 600 }}>
                  Search
                </Button>
                <IconButton onClick={clearFilters} color="secondary" title="Clear all filters">
                  <ClearIcon />
                </IconButton>
              </Grid>
            </Grid>
          </Box>

          <Divider sx={{ my: 2.5 }} />

          {/* Checklist Multi-Select Groups */}
          <Grid container spacing={4}>
            {/* Scopes */}
            <Grid item xs={12} sm={4}>
              <Typography variant="subtitle2" color="text.secondary" gutterBottom fontWeight={600}>
                GHG Protocol Scopes
              </Typography>
              <FormGroup row>
                {scopes.map(sc => (
                  <FormControlLabel
                    key={sc}
                    control={
                      <Checkbox
                        size="small"
                        checked={selectedScopes.includes(sc)}
                        onChange={(e) => {
                          if (e.target.checked) setSelectedScopes([...selectedScopes, sc]);
                          else setSelectedScopes(selectedScopes.filter(item => item !== sc));
                          setPage(0);
                        }}
                      />
                    }
                    label={`Scope ${sc}`}
                  />
                ))}
              </FormGroup>
            </Grid>

            {/* Ingestion Sources */}
            <Grid item xs={12} sm={4}>
              <Typography variant="subtitle2" color="text.secondary" gutterBottom fontWeight={600}>
                Data Inflow Feeds
              </Typography>
              <FormGroup row>
                {sources.map(src => (
                  <FormControlLabel
                    key={src.value}
                    control={
                      <Checkbox
                        size="small"
                        checked={selectedSources.includes(src.value)}
                        onChange={(e) => {
                          if (e.target.checked) setSelectedSources([...selectedSources, src.value]);
                          else setSelectedSources(selectedSources.filter(item => item !== src.value));
                          setPage(0);
                        }}
                      />
                    }
                    label={src.label}
                  />
                ))}
              </FormGroup>
            </Grid>

            {/* Workflow statuses */}
            <Grid item xs={12} sm={4}>
              <Typography variant="subtitle2" color="text.secondary" gutterBottom fontWeight={600}>
                Verification State
              </Typography>
              <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                {statuses.map(st => {
                  const active = selectedStatuses.includes(st);
                  return (
                    <Button
                      key={st}
                      variant={active ? 'contained' : 'outlined'}
                      color={active ? 'primary' : 'inherit'}
                      size="small"
                      onClick={() => {
                        if (active) setSelectedStatuses(selectedStatuses.filter(item => item !== st));
                        else setSelectedStatuses([...selectedStatuses, st]);
                        setPage(0);
                      }}
                      sx={{ textTransform: 'capitalize', py: 0.25, px: 1, borderRadius: 3, fontSize: '0.75rem' }}
                    >
                      {st}
                    </Button>
                  );
                })}
              </Box>
            </Grid>
          </Grid>
        </CardContent>
      </Card>

      {/* Bulk action toolbar */}
      {selectedIds.length > 0 && (
        <Alert
          severity="info"
          icon={<FactCheckIcon />}
          sx={{ mb: 3, display: 'flex', alignItems: 'center', fontWeight: 600 }}
          action={
            <Box sx={{ display: 'flex', gap: 2 }}>
              <Button
                variant="contained"
                color="primary"
                size="small"
                startIcon={<CheckCircleOutlineIcon />}
                disabled={bulkProcessing}
                onClick={() => handleBulkAction('review')}
              >
                Mark as Reviewed
              </Button>
              <Button
                variant="contained"
                color="success"
                size="small"
                startIcon={<CheckCircleOutlineIcon />}
                disabled={bulkProcessing}
                onClick={() => handleBulkAction('approve')}
              >
                Approve Selected
              </Button>
            </Box>
          }
        >
          {selectedIds.length} emission record(s) selected for bulk analyst verification
        </Alert>
      )}

      {bulkMsg && (
        <Alert severity={bulkMsg.type} sx={{ mb: 3 }} onClose={() => setBulkMsg(null)}>
          {bulkMsg.text}
        </Alert>
      )}

      {/* Ledger Table */}
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
                  <TableCell padding="checkbox">
                    <Checkbox
                      indeterminate={selectedIds.length > 0 && selectedIds.length < records.length}
                      checked={records.length > 0 && selectedIds.length === records.length}
                      onChange={handleSelectAll}
                    />
                  </TableCell>
                  <TableCell sx={{ fontWeight: 600 }}>Verification</TableCell>
                  <TableCell sx={{ fontWeight: 600 }}>Scope</TableCell>
                  <TableCell sx={{ fontWeight: 600 }}>Emission Category</TableCell>
                  <TableCell sx={{ fontWeight: 600 }}>Activity Date</TableCell>
                  <TableCell sx={{ fontWeight: 600 }}>Raw Quantity</TableCell>
                  <TableCell sx={{ fontWeight: 600 }}>Calculated CO₂e (t)</TableCell>
                  <TableCell sx={{ fontWeight: 600 }}>Source</TableCell>
                  <TableCell sx={{ fontWeight: 600 }} align="center">Quality</TableCell>
                  <TableCell sx={{ fontWeight: 600 }} align="right">Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {records.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={10} align="center" sx={{ py: 6, color: 'text.secondary' }}>
                      No transactions match the selected filters.
                    </TableCell>
                  </TableRow>
                ) : (
                  records.map((rec) => {
                    const hasFlags = rec.flags && rec.flags.length > 0;
                    return (
                      <TableRow key={rec.id} hover selected={selectedIds.includes(rec.id)}>
                        <TableCell padding="checkbox">
                          <Checkbox
                            checked={selectedIds.includes(rec.id)}
                            onChange={() => handleSelectOne(rec.id)}
                            disabled={rec.status === 'locked'}
                          />
                        </TableCell>
                        <TableCell>
                          <StatusChip status={rec.status} />
                        </TableCell>
                        <TableCell>
                          <ScopeChip scope={rec.scope} />
                        </TableCell>
                        <TableCell sx={{ textTransform: 'capitalize', fontWeight: 600 }}>
                          {rec.category.replace('_', ' ')}
                        </TableCell>
                        <TableCell>
                          {rec.activity_date}
                        </TableCell>
                        <TableCell>
                          {rec.original_quantity_value ? Number(rec.original_quantity_value).toLocaleString(undefined, { maximumFractionDigits: 2 }) : '-'} {rec.original_quantity_unit || rec.quantity_unit}
                        </TableCell>
                        <TableCell sx={{ fontWeight: 700, color: 'primary.dark' }}>
                          {rec.co2e_tonnes ? Number(rec.co2e_tonnes).toFixed(6) : '-'}
                        </TableCell>
                        <TableCell sx={{ textTransform: 'uppercase', fontSize: '0.8rem', fontWeight: 600 }}>
                          {rec.data_source_type}
                        </TableCell>
                        <TableCell align="center">
                          {hasFlags ? (
                            <Tooltip title={rec.flags.join(', ')} arrow>
                              <IconButton color="error" size="small">
                                <WarningIcon fontSize="small" />
                              </IconButton>
                            </Tooltip>
                          ) : (
                            '-'
                          )}
                        </TableCell>
                        <TableCell align="right">
                          <IconButton
                            color="primary"
                            size="small"
                            onClick={() => navigate(`/records/${rec.id}`)}
                            title="Verify Record"
                          >
                            <VisibilityIcon fontSize="small" />
                          </IconButton>
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

export default Records;
