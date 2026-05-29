import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import Typography from '@mui/material/Typography';
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import Box from '@mui/material/Box';
import MenuItem from '@mui/material/MenuItem';
import TextField from '@mui/material/TextField';
import Button from '@mui/material/Button';
import Alert from '@mui/material/Alert';
import CircularProgress from '@mui/material/CircularProgress';
import Grid from '@mui/material/Grid';
import Divider from '@mui/material/Divider';
import Paper from '@mui/material/Paper';
import Table from '@mui/material/Table';
import TableBody from '@mui/material/TableBody';
import TableCell from '@mui/material/TableCell';
import TableContainer from '@mui/material/TableContainer';
import TableHead from '@mui/material/TableHead';
import TableRow from '@mui/material/TableRow';
import CloudUploadIcon from '@mui/icons-material/CloudUpload';
import ErrorIcon from '@mui/icons-material/Error';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import { getDataSources, uploadFile } from '../api/client';
import type { DataSource, IngestionJob } from '../types';
import StatusChip from '../components/StatusChip';

const Upload: React.FC = () => {
  const navigate = useNavigate();
  const [sources, setSources] = useState<DataSource[]>([]);
  const [selectedSourceId, setSelectedSourceId] = useState<string>('');
  
  const [file, setFile] = useState<File | null>(null);
  const [dragActive, setDragActive] = useState<boolean>(false);
  
  const [uploading, setUploading] = useState<boolean>(false);
  const [result, setResult] = useState<IngestionJob | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getDataSources()
      .then((res) => {
        setSources(res);
        if (res.length > 0) {
          setSelectedSourceId(res[0].id);
        }
      })
      .catch((err) => {
        setError(err.message || 'Failed to load configured data feeds.');
      });
  }, []);

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const droppedFile = e.dataTransfer.files[0];
      if (droppedFile.name.endsWith('.csv')) {
        setFile(droppedFile);
        setError(null);
      } else {
        setError('Only CSV files (.csv) are supported.');
      }
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const selectedFile = e.target.files[0];
      if (selectedFile.name.endsWith('.csv')) {
        setFile(selectedFile);
        setError(null);
      } else {
        setError('Only CSV files (.csv) are supported.');
      }
    }
  };

  const handleUpload = () => {
    if (!selectedSourceId || !file) {
      setError('Please select a data source and attach a file first.');
      return;
    }

    setUploading(true);
    setError(null);
    setResult(null);

    uploadFile(selectedSourceId, file)
      .then((res) => {
        setResult(res);
        setUploading(false);
      })
      .catch((err) => {
        const errorMsg = err.response?.data?.error || err.message || 'Ingestion failed.';
        setError(errorMsg);
        setUploading(false);
      });
  };

  const selectedSource = sources.find(s => s.id === selectedSourceId);

  return (
    <Box sx={{ maxWidth: 900, mx: 'auto' }}>
      <Typography variant="h4" gutterBottom sx={{ mb: 4, fontWeight: 700 }}>
        Data Ingestion Hub
      </Typography>

      <Grid container spacing={4}>
        {/* Upload configuration form */}
        <Grid size={{ xs: 12, md: result ? 5 : 12 }}>
          <Card>
            <CardContent sx={{ p: 4 }}>
              <Typography variant="h6" gutterBottom sx={{ mb: 3, fontWeight: 600 }}>
                Configure Import Ingestion
              </Typography>
              
              {/* Step 1: Select source */}
              <TextField
                select
                fullWidth
                label="Target Data Source Feeds"
                value={selectedSourceId}
                onChange={(e) => setSelectedSourceId(e.target.value)}
                sx={{ mb: 3 }}
                helperText={selectedSource?.description || ''}
              >
                {sources.map((src) => (
                  <MenuItem key={src.id} value={src.id}>
                    {src.name} ({src.source_type.toUpperCase()})
                  </MenuItem>
                ))}
              </TextField>

              {/* Step 2: Drag and drop dropzone */}
              <Box
                onDragEnter={handleDrag}
                onDragOver={handleDrag}
                onDragLeave={handleDrag}
                onDrop={handleDrop}
                sx={{
                  border: '2px dashed',
                  borderColor: dragActive ? 'primary.main' : 'divider',
                  bgcolor: dragActive ? 'primary.main' + '08' : 'background.default',
                  borderRadius: 2,
                  p: 4,
                  textAlign: 'center',
                  cursor: 'pointer',
                  position: 'relative',
                  mb: 4,
                  transition: 'all 0.2s ease',
                  '&:hover': {
                    borderColor: 'primary.main',
                    bgcolor: 'primary.main' + '04',
                  }
                }}
              >
                <input
                  type="file"
                  id="csv-file-input"
                  accept=".csv"
                  style={{ display: 'none' }}
                  onChange={handleFileChange}
                />
                <label htmlFor="csv-file-input" style={{ cursor: 'pointer', display: 'block', width: '100%' }}>
                  <CloudUploadIcon sx={{ fontSize: 48, color: 'text.secondary', mb: 2 }} />
                  <Typography variant="subtitle1" gutterBottom sx={{ fontWeight: 600 }}>
                    {file ? file.name : 'Select or drag & drop CSV file'}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    {file ? `${(file.size / 1024).toFixed(1)} KB` : 'Only standard flat CSV spreadsheets are supported'}
                  </Typography>
                </label>
              </Box>

              {error && (
                <Alert severity="error" sx={{ mb: 3 }}>
                  {error}
                </Alert>
              )}

              {/* Action buttons */}
              <Button
                variant="contained"
                fullWidth
                size="large"
                startIcon={uploading ? <CircularProgress size={20} color="inherit" /> : <CloudUploadIcon />}
                disabled={uploading || !file || !selectedSourceId}
                onClick={handleUpload}
                sx={{ py: 1.5, fontWeight: 700 }}
              >
                {uploading ? 'Processing & Normalizing...' : 'Upload & Standardize'}
              </Button>
            </CardContent>
          </Card>
        </Grid>

        {/* Results Workspace */}
        {result && (
          <Grid size={{ xs: 12, md: 7 }}>
            <Card sx={{ height: '100%' }}>
              <CardContent sx={{ p: 4, height: '100%', display: 'flex', flexDirection: 'column' }}>
                <Typography variant="h6" gutterBottom sx={{ mb: 3, fontWeight: 600 }}>
                  Ingestion Job Result summary
                </Typography>
                
                {/* Result header banner */}
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 3 }}>
                  {result.status === 'completed' ? (
                    <CheckCircleIcon color="success" sx={{ fontSize: 36 }} />
                  ) : (
                    <ErrorIcon color="warning" sx={{ fontSize: 36 }} />
                  )}
                  <Box>
                    <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>
                      {result.file_name}
                    </Typography>
                    <Box sx={{ display: 'flex', gap: 1, alignItems: 'center', mt: 0.5 }}>
                      <Typography variant="body2" color="text.secondary">
                        Verification Status:
                      </Typography>
                      <StatusChip status={result.status} />
                    </Box>
                  </Box>
                </Box>

                <Divider sx={{ mb: 3 }} />

                {/* Import statistics */}
                <Grid container spacing={2} sx={{ mb: 4 }}>
                  <Grid size={4}>
                    <Paper variant="outlined" sx={{ p: 2, textAlign: 'center' }}>
                      <Typography variant="h5" sx={{ fontWeight: 700 }}>
                        {result.total_rows}
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        Total Rows
                      </Typography>
                    </Paper>
                  </Grid>
                  <Grid size={4}>
                    <Paper variant="outlined" sx={{ p: 2, textAlign: 'center', borderLeft: '3px solid #2E7D32' }}>
                      <Typography variant="h5" color="#2E7D32" sx={{ fontWeight: 700 }}>
                        {result.successful_rows}
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        Successfully Normalized
                      </Typography>
                    </Paper>
                  </Grid>
                  <Grid size={4}>
                    <Paper variant="outlined" sx={{ p: 2, textAlign: 'center', borderLeft: result.failed_rows > 0 ? '3px solid #D32F2F' : '1px solid #E0E0E0' }}>
                      <Typography variant="h5" color={result.failed_rows > 0 ? '#D32F2F' : 'text.primary'} sx={{ fontWeight: 700 }}>
                        {result.failed_rows}
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        Failed / Flagged
                      </Typography>
                    </Paper>
                  </Grid>
                </Grid>

                {/* Ingestion Actions */}
                {result.successful_rows > 0 && (
                  <Box sx={{ mb: 4, display: 'flex', gap: 2 }}>
                    <Button
                      variant="contained"
                      color="success"
                      onClick={() => navigate('/records')}
                      fullWidth
                    >
                      Verify Normalized Emissions
                    </Button>
                  </Box>
                )}

                {/* Error diagnostics */}
                {result.error_summary && result.error_summary.length > 0 && (
                  <Box sx={{ flexGrow: 1, display: 'flex', flexDirection: 'column' }}>
                    <Typography variant="subtitle2" color="error" sx={{ mb: 1.5, fontWeight: 700 }}>
                      Ingestion Quality & Normalization Errors
                    </Typography>
                    <TableContainer component={Paper} sx={{ flexGrow: 1, maxHeight: 200, overflow: 'auto', border: '1px solid #E0E0E0', boxShadow: 'none' }}>
                      <Table stickyHeader size="small">
                        <TableHead>
                          <TableRow>
                            <TableCell sx={{ fontWeight: 600 }}>Row</TableCell>
                            <TableCell sx={{ fontWeight: 600 }}>Field</TableCell>
                            <TableCell sx={{ fontWeight: 600 }}>Error Diagnostic</TableCell>
                          </TableRow>
                        </TableHead>
                        <TableBody>
                          {result.error_summary.map((err, idx) => (
                            <TableRow key={idx}>
                              <TableCell>{err.row === 0 ? 'File' : err.row}</TableCell>
                              <TableCell sx={{ textTransform: 'capitalize', fontWeight: 600 }}>{err.field}</TableCell>
                              <TableCell color="error">{err.message}</TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </TableContainer>
                  </Box>
                )}
              </CardContent>
            </Card>
          </Grid>
        )}
      </Grid>
    </Box>
  );
};

export default Upload;
