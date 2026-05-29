import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import Box from '@mui/material/Box';
import Grid from '@mui/material/Grid';
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import Typography from '@mui/material/Typography';
import Button from '@mui/material/Button';
import TextField from '@mui/material/TextField';
import Divider from '@mui/material/Divider';
import Alert from '@mui/material/Alert';
import Paper from '@mui/material/Paper';
import Table from '@mui/material/Table';
import TableBody from '@mui/material/TableBody';
import TableCell from '@mui/material/TableCell';
import TableContainer from '@mui/material/TableContainer';
import TableRow from '@mui/material/TableRow';
import CircularProgress from '@mui/material/CircularProgress';
import Stepper from '@mui/material/Stepper';
import Step from '@mui/material/Step';
import StepLabel from '@mui/material/StepLabel';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import WarningIcon from '@mui/icons-material/Warning';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import LockIcon from '@mui/icons-material/Lock';
import GavelIcon from '@mui/icons-material/Gavel';
import ReportProblemIcon from '@mui/icons-material/ReportProblem';
import type { EmissionRecord } from '../types';
import { getEmissionRecord, reviewRecord } from '../api/client';
import StatusChip from '../components/StatusChip';
import ScopeChip from '../components/ScopeChip';

const RecordDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [record, setRecord] = useState<EmissionRecord | null>(null);
  
  // Action form state
  const [note, setNote] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  const fetchRecord = () => {
    if (!id) return;
    setLoading(true);
    setError(null);
    getEmissionRecord(id)
      .then((res) => {
        setRecord(res);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message || 'Failed to load record details.');
        setLoading(false);
      });
  };

  useEffect(() => {
    fetchRecord();
  }, [id]);

  const handleAction = (actionName: 'review' | 'flag' | 'approve' | 'reject' | 'lock') => {
    if (!record || !id) return;
    
    if (actionName === 'reject' && !note.strip()) {
      setActionError('Analyst justification notes are required for rejections.');
      return;
    }
    
    setSubmitting(true);
    setActionError(null);
    
    reviewRecord(id, actionName, note, 'system_analyst')
      .then(() => {
        setSubmitting(false);
        setNote('');
        fetchRecord(); // Refresh page data
      })
      .catch((err) => {
        setActionError(err.response?.data?.error || err.message || 'Workflow action execution failed.');
        setSubmitting(false);
      });
  };

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}>
        <CircularProgress />
      </Box>
    );
  }

  if (error || !record) {
    return <Alert severity="error">Error loading record: {error}</Alert>;
  }

  const isPendingOrFlagged = record.status === 'pending' || record.status === 'flagged';
  const isReviewed = record.status === 'reviewed';
  const isApproved = record.status === 'approved';
  const isLocked = record.status === 'locked';
  const isRejected = record.status === 'rejected';

  const showNotesInput = isPendingOrFlagged || isReviewed || isApproved || isRejected;

  // Check if original quantity was converted
  const wasConverted = record.original_quantity_value !== null && 
    (Number(record.original_quantity_value) !== Number(record.quantity_value) || 
     record.original_quantity_unit !== record.quantity_unit);

  return (
    <Box>
      {/* Back button */}
      <Button
        startIcon={<ArrowBackIcon />}
        onClick={() => navigate('/records')}
        sx={{ mb: 4, fontWeight: 600 }}
      >
        Return to Emission Ledger
      </Button>

      {/* Title section */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 4 }}>
        <Box>
          <Typography variant="h4" sx={{ fontWeight: 700, mb: 1 }}>
            Verify normalized transaction
          </Typography>
          <Typography variant="body2" color="text.secondary">
            System ID: {record.id}
          </Typography>
        </Box>
        <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
          <ScopeChip scope={record.scope} size="medium" />
          <StatusChip status={record.status} size="medium" />
        </Box>
      </Box>

      <Grid container spacing={4}>
        {/* LEFT COLUMN: Ledger Details & Calculations */}
        <Grid item xs={12} md={7}>
          {/* 1. Normalized Core Ledger Details */}
          <Card sx={{ mb: 4 }}>
            <CardContent sx={{ p: 4 }}>
              <Typography variant="h6" gutterBottom sx={{ mb: 3, fontWeight: 700 }}>
                Normalized Emission Record
              </Typography>
              
              <TableContainer component={Paper} sx={{ boxShadow: 'none', border: '1px solid #E0E0E0' }}>
                <Table size="small">
                  <TableBody>
                    <TableRow hover>
                      <TableCell sx={{ fontWeight: 600, width: '35%' }}>Emissions Scope</TableCell>
                      <TableCell>Scope {record.scope}</TableCell>
                    </TableRow>
                    <TableRow hover>
                      <TableCell sx={{ fontWeight: 600 }}>Standard Category</TableCell>
                      <TableCell sx={{ textTransform: 'capitalize' }}>{record.category.replace('_', ' ')}</TableCell>
                    </TableRow>
                    <TableRow hover>
                      <TableCell sx={{ fontWeight: 600 }}>Description</TableCell>
                      <TableCell>{record.description}</TableCell>
                    </TableRow>
                    <TableRow hover>
                      <TableCell sx={{ fontWeight: 600 }}>Activity Date</TableCell>
                      <TableCell>{record.activity_date}</TableCell>
                    </TableRow>
                    {record.reporting_period_start && (
                      <TableRow hover>
                        <TableCell sx={{ fontWeight: 600 }}>Billing Period</TableCell>
                        <TableCell>
                          {record.reporting_period_start} to {record.reporting_period_end}
                        </TableCell>
                      </TableRow>
                    )}
                    <TableRow hover>
                      <TableCell sx={{ fontWeight: 600 }}>Standard Quantity</TableCell>
                      <TableCell sx={{ fontWeight: 700 }}>
                        {Number(record.quantity_value).toLocaleString(undefined, { maximumFractionDigits: 4 })} {record.quantity_unit}
                      </TableCell>
                    </TableRow>
                    <TableRow hover>
                      <TableCell sx={{ fontWeight: 600 }}>Carbon Footprint</TableCell>
                      <TableCell sx={{ fontWeight: 800, color: 'primary.dark', fontSize: '1rem' }}>
                        {Number(record.co2e_tonnes).toFixed(6)} tCO₂e ({Number(record.co2e_kg).toLocaleString(undefined, { maximumFractionDigits: 2 })} kgCO₂e)
                      </TableCell>
                    </TableRow>
                  </TableBody>
                </Table>
              </TableContainer>
            </CardContent>
          </Card>

          {/* 2. Unit conversion trace */}
          {wasConverted && (
            <Card sx={{ mb: 4, bgcolor: 'primary.main' + '04', border: '1px solid ' + 'rgba(0, 105, 92, 0.15)' }}>
              <CardContent sx={{ p: 4 }}>
                <Typography variant="h6" color="primary" gutterBottom sx={{ mb: 2, fontWeight: 700 }}>
                  Standardization & Unit Conversion Log
                </Typography>
                <Grid container spacing={3}>
                  <Grid item xs={5} textAlign="center">
                    <Paper sx={{ p: 2, bgcolor: 'background.paper' }}>
                      <Typography variant="h6" sx={{ fontWeight: 700 }}>
                        {Number(record.original_quantity_value).toLocaleString(undefined, { maximumFractionDigits: 4 })}
                      </Typography>
                      <Typography variant="caption" color="text.secondary" sx={{ textTransform: 'uppercase' }}>
                        Original Unit ({record.original_quantity_unit})
                      </Typography>
                    </Paper>
                  </Grid>
                  <Grid item xs={2} sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                    <Typography variant="h5" color="primary" sx={{ fontWeight: 700 }}>→</Typography>
                  </Grid>
                  <Grid item xs={5} textAlign="center">
                    <Paper sx={{ p: 2, bgcolor: 'background.paper', border: '1.5px solid #00695C' }}>
                      <Typography variant="h6" color="primary" sx={{ fontWeight: 700 }}>
                        {Number(record.quantity_value).toLocaleString(undefined, { maximumFractionDigits: 4 })}
                      </Typography>
                      <Typography variant="caption" color="primary" sx={{ textTransform: 'uppercase', fontWeight: 600 }}>
                        Normalized Unit ({record.quantity_unit})
                      </Typography>
                    </Paper>
                  </Grid>
                </Grid>
              </CardContent>
            </Card>
          )}

          {/* 3. Mathematical Formula Trace */}
          <Card sx={{ mb: 4 }}>
            <CardContent sx={{ p: 4 }}>
              <Typography variant="h6" gutterBottom sx={{ mb: 3, fontWeight: 700 }}>
                Carbon footprint Audit Trail
              </Typography>
              
              <Paper variant="outlined" sx={{ p: 3, mb: 3, bgcolor: 'background.default', textAlign: 'center' }}>
                <Typography variant="caption" color="text.secondary" display="block" gutterBottom sx={{ fontWeight: 600 }}>
                  CALCULATION FORMULA
                </Typography>
                <Typography variant="h6" sx={{ fontStyle: 'italic', color: 'primary.dark', fontWeight: 700 }}>
                  {Number(record.quantity_value).toLocaleString(undefined, { maximumFractionDigits: 4 })} {record.quantity_unit} × {Number(record.emission_factor_value).toFixed(6)} {record.original_quantity_unit === 'spend_usd' ? 'kgCO2e/spend' : 'kgCO2e/' + record.quantity_unit}
                </Typography>
                <Typography variant="h5" sx={{ mt: 2, color: 'text.primary', fontWeight: 800 }}>
                  = {Number(record.co2e_kg).toLocaleString(undefined, { maximumFractionDigits: 2 })} kgCO₂e ({Number(record.co2e_tonnes).toFixed(6)} tCO₂e)
                </Typography>
              </Paper>

              <TableContainer component={Paper} sx={{ boxShadow: 'none', border: '1px solid #E0E0E0' }}>
                <Table size="small">
                  <TableBody>
                    <TableRow hover>
                      <TableCell sx={{ fontWeight: 600, width: '35%' }}>Used Emission Factor</TableCell>
                      <TableCell sx={{ fontFamily: 'monospace' }}>
                        {Number(record.emission_factor_value).toFixed(6)}
                      </TableCell>
                    </TableRow>
                    <TableRow hover>
                      <TableCell sx={{ fontWeight: 600 }}>Factor Source Reference</TableCell>
                      <TableCell>{record.emission_factor ? record.flags.includes('Spend-based estimation') ? 'EEIO spend fallback' : 'DEFRA 2024 Conversion Factors' : 'Seeded Standard Factor'}</TableCell>
                    </TableRow>
                  </TableBody>
                </Table>
              </TableContainer>
            </CardContent>
          </Card>

          {/* 4. Validation/Anomaly Flags */}
          {record.flags && record.flags.length > 0 && (
            <Card sx={{ mb: 4, borderLeft: '4px solid #D32F2F' }}>
              <CardContent sx={{ p: 4 }}>
                <Typography variant="h6" color="error" gutterBottom sx={{ mb: 2, display: 'flex', alignItems: 'center', gap: 1, fontWeight: 700 }}>
                  <WarningIcon />
                  Quality Validation Alerts ({record.flags.length})
                </Typography>
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
                  {record.flags.map((flag, idx) => (
                    <Alert key={idx} severity={flag.startsWith('Anomaly') ? 'error' : 'warning'} sx={{ py: 0.5 }}>
                      {flag}
                    </Alert>
                  ))}
                </Box>
              </CardContent>
            </Card>
          )}

          {/* 5. Immutable raw record payload */}
          <Card>
            <CardContent sx={{ p: 4 }}>
              <Typography variant="h6" gutterBottom sx={{ mb: 3, fontWeight: 700 }}>
                Raw Source Record (Ingested Payload)
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
                This is the raw data captured directly from the CSV input. It is stored as immutable JSONB in PostgreSQL.
              </Typography>

              <TableContainer component={Paper} sx={{ maxHeight: 300, overflow: 'auto', border: '1px solid #E0E0E0', boxShadow: 'none' }}>
                <Table size="small" stickyHeader>
                  <TableHead>
                    <TableRow>
                      <TableCell sx={{ fontWeight: 600, bgcolor: 'background.default' }}>Original Field</TableCell>
                      <TableCell sx={{ fontWeight: 600, bgcolor: 'background.default' }}>Raw Value</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {Object.entries(record.raw_data || {}).map(([key, val]) => (
                      <TableRow key={key} hover>
                        <TableCell sx={{ fontFamily: 'monospace', fontWeight: 600 }}>{key}</TableCell>
                        <TableCell sx={{ fontFamily: 'monospace', color: 'secondary.dark' }}>
                          {val === '' ? <Typography variant="caption" sx={{ fontStyle: 'italic', color: 'text.disabled' }}>NULL</Typography> : String(val)}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            </CardContent>
          </Card>
        </Grid>

        {/* RIGHT COLUMN: Review panel & timeline history */}
        <Grid item xs={12} md={5}>
          {/* Action workspace */}
          <Card sx={{ mb: 4, position: 'sticky', top: 96 }}>
            <CardContent sx={{ p: 4 }}>
              <Typography variant="h6" gutterBottom sx={{ mb: 3, fontWeight: 700 }}>
                analyst review workspace
              </Typography>

              {/* Action error banner */}
              {actionError && (
                <Alert severity="error" sx={{ mb: 3 }} onClose={() => setActionError(null)}>
                  {actionError}
                </Alert>
              )}

              {/* Locked state indicator */}
              {isLocked ? (
                <Paper sx={{ p: 3, textAlign: 'center', bgcolor: 'secondary.light' + '10', border: '1.5px solid #757575' }}>
                  <LockIcon sx={{ fontSize: 48, color: 'text.disabled', mb: 2 }} />
                  <Typography variant="h6" gutterBottom sx={{ fontWeight: 700 }}>
                    Sealed & Locked for Audit
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    This emission transaction has been reviewed, approved, and chronologically sealed. No further modifications or workflow transitions are permitted.
                  </Typography>
                </Paper>
              ) : (
                <Box>
                  <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
                    Move this record through the verification pipeline. Edits or actions will be immutably recorded in the ledger's audit log.
                  </Typography>

                  {/* Dynamic Action Buttons based on status */}
                  <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mb: 4 }}>
                    {isPendingOrFlagged && (
                      <>
                        <Button
                          variant="contained"
                          color="primary"
                          size="large"
                          disabled={submitting}
                          onClick={() => handleAction('review')}
                        >
                          Mark as Reviewed
                        </Button>
                        <Button
                          variant="outlined"
                          color="error"
                          size="large"
                          disabled={submitting || record.status === 'flagged'}
                          onClick={() => handleAction('flag')}
                        >
                          Flag Anomalies
                        </Button>
                      </>
                    )}

                    {isReviewed && (
                      <>
                        <Button
                          variant="contained"
                          color="success"
                          size="large"
                          disabled={submitting}
                          onClick={() => handleAction('approve')}
                        >
                          Approve Emissions
                        </Button>
                        <Button
                          variant="outlined"
                          color="error"
                          size="large"
                          disabled={submitting}
                          onClick={() => handleAction('reject')}
                        >
                          Reject / Request Clarification
                        </Button>
                      </>
                    )}

                    {isApproved && (
                      <Button
                        variant="contained"
                        color="warning"
                        size="large"
                        startIcon={<GavelIcon />}
                        disabled={submitting}
                        onClick={() => handleAction('lock')}
                      >
                        Lock for Annual Audit
                      </Button>
                    )}

                    {isRejected && (
                      <Button
                        variant="contained"
                        color="secondary"
                        size="large"
                        disabled={submitting}
                        onClick={() => handleAction('review')}
                      >
                        Return to Reviewed State
                      </Button>
                    )}
                  </Box>

                  {/* Notes / Reason justify */}
                  {showNotesInput && (
                    <TextField
                      fullWidth
                      multiline
                      rows={3}
                      label="Analyst Justification Notes"
                      placeholder={isReviewed ? "Justification is required if rejecting..." : "Add notes, overrides justification, or explain anomaly flags..."}
                      value={note}
                      onChange={(e) => setNote(e.target.value)}
                      sx={{ mb: 2 }}
                    />
                  )}
                </Box>
              )}

              <Divider sx={{ my: 3 }} />

              {/* Timeline review history */}
              <Typography variant="subtitle1" gutterBottom sx={{ mb: 2, fontWeight: 700 }}>
                Verification Timeline & History
              </Typography>

              {record.review_actions && record.review_actions.length === 0 ? (
                <Typography variant="body2" color="text.secondary" sx={{ fontStyle: 'italic' }}>
                  No actions taken on this record yet.
                </Typography>
              ) : (
                <Stepper orientation="vertical" activeStep={-1} sx={{ pl: 1 }}>
                  {(record.review_actions || []).map((action) => (
                    <Step key={action.id} expanded>
                      <StepLabel
                        icon={
                          action.action === 'approve' ? (
                            <CheckCircleIcon color="success" fontSize="small" />
                          ) : action.action === 'lock' ? (
                            <LockIcon color="warning" fontSize="small" />
                          ) : action.action === 'flag' ? (
                            <ReportProblemIcon color="error" fontSize="small" />
                          ) : (
                            <CheckCircleIcon color="primary" fontSize="small" />
                          )
                        }
                      >
                        <Box sx={{ display: 'flex', flexDirection: 'column' }}>
                          <Typography variant="subtitle2" sx={{ fontWeight: 700 }}>
                            {action.action.toUpperCase()} by {action.performed_by}
                          </Typography>
                          <Typography variant="caption" color="text.secondary">
                            {new Date(action.created_at).toLocaleString()}
                          </Typography>
                          {action.reason && (
                            <Typography variant="body2" sx={{ mt: 1, p: 1.5, bgcolor: 'background.default', borderRadius: 1, border: '1px solid #E0E0E0', fontStyle: 'italic' }}>
                              "{action.reason}"
                            </Typography>
                          )}
                        </Box>
                      </StepLabel>
                    </Step>
                  ))}
                </Stepper>
              )}
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
};

export default RecordDetail;
