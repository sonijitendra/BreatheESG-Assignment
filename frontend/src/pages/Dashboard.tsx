import React, { useEffect, useState } from 'react';
import Grid from '@mui/material/Grid';
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import Typography from '@mui/material/Typography';
import Box from '@mui/material/Box';
import Table from '@mui/material/Table';
import TableBody from '@mui/material/TableBody';
import TableCell from '@mui/material/TableCell';
import TableContainer from '@mui/material/TableContainer';
import TableHead from '@mui/material/TableHead';
import TableRow from '@mui/material/TableRow';
import Paper from '@mui/material/Paper';
import Skeleton from '@mui/material/Skeleton';
import Alert from '@mui/material/Alert';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';
import { getDashboardSummary } from '../api/client';
import type { DashboardSummary } from '../types';
import StatusChip from '../components/StatusChip';

const Dashboard: React.FC = () => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<DashboardSummary | null>(null);

  useEffect(() => {
    getDashboardSummary()
      .then((res) => {
        setData(res);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message || 'Failed to fetch dashboard summary.');
        setLoading(false);
      });
  }, []);

  if (loading) {
    return (
      <Box sx={{ width: '100%' }}>
        <Skeleton variant="text" sx={{ fontSize: '2rem', mb: 4, width: '40%' }} />
        <Grid container spacing={3} sx={{ mb: 4 }}>
          {[1, 2, 3, 4].map((i) => (
            <Grid item xs={12} sm={6} md={3} key={i}>
              <Card sx={{ height: 120 }}>
                <CardContent>
                  <Skeleton variant="rectangular" height={20} sx={{ mb: 1, width: '60%' }} />
                  <Skeleton variant="rectangular" height={40} sx={{ width: '80%' }} />
                </CardContent>
              </Card>
            </Grid>
          ))}
        </Grid>
        <Grid container spacing={3}>
          <Grid item xs={12} md={7}>
            <Skeleton variant="rectangular" height={350} />
          </Grid>
          <Grid item xs={12} md={5}>
            <Skeleton variant="rectangular" height={350} />
          </Grid>
        </Grid>
      </Box>
    );
  }

  if (error || !data) {
    return <Alert severity="error">Error loading dashboard: {error}</Alert>;
  }

  // Calculate specific metrics
  const pendingCount = data.by_status.find(s => s.status === 'pending')?.count || 0;
  const flaggedCount = data.by_status.find(s => s.status === 'flagged')?.count || 0;
  const totalPending = pendingCount + flaggedCount;

  const approvedCount = data.by_status.find(s => s.status === 'approved')?.count || 0;
  const lockedCount = data.by_status.find(s => s.status === 'locked')?.count || 0;
  const totalApproved = approvedCount + lockedCount;

  // Prepare chart data
  const scopeChartData = [
    { name: 'Scope 1 (Direct)', co2e_tonnes: data.by_scope.find(s => s.scope === 1)?.co2e_tonnes || 0 },
    { name: 'Scope 2 (Electricity)', co2e_tonnes: data.by_scope.find(s => s.scope === 2)?.co2e_tonnes || 0 },
    { name: 'Scope 3 (Value Chain)', co2e_tonnes: data.by_scope.find(s => s.scope === 3)?.co2e_tonnes || 0 },
  ];

  const sourceChartData = data.by_source.map(src => ({
    name: src.source_type === 'sap' ? 'SAP Fuels' : src.source_type === 'utility' ? 'Utility Electricity' : 'Travel Expenses',
    co2e_tonnes: src.co2e_tonnes,
  }));

  const statusColors = ['#F57C00', '#D32F2F', '#1976D2', '#2E7D32', '#C2185B', '#757575'];
  const statusPieData = data.by_status.map(s => ({
    name: s.status.charAt(0).toUpperCase() + s.status.slice(1),
    value: s.count,
  }));

  return (
    <Box>
      <Typography variant="h4" gutterBottom sx={{ mb: 4, fontWeight: 700, color: 'text.primary' }}>
        Sustainability Executive Dashboard
      </Typography>

      {/* KPI Cards Grid */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid item xs={12} sm={6} md={3}>
          <Card sx={{ borderLeft: '4px solid #00695C' }}>
            <CardContent>
              <Typography color="text.secondary" variant="subtitle2" gutterBottom>
                Total Ingested Transactions
              </Typography>
              <Typography variant="h4" sx={{ fontWeight: 700, color: 'text.primary' }}>
                {data.total_records.toLocaleString()}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card sx={{ borderLeft: '4px solid #1565C0' }}>
            <CardContent>
              <Typography color="text.secondary" variant="subtitle2" gutterBottom>
                Total Carbon Footprint (tCO₂e)
              </Typography>
              <Typography variant="h4" sx={{ fontWeight: 700, color: '#1565C0' }}>
                {data.total_co2e_tonnes.toFixed(4)}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card sx={{ borderLeft: '4px solid #F57C00' }}>
            <CardContent>
              <Typography color="text.secondary" variant="subtitle2" gutterBottom>
                Records Pending Review / Action
              </Typography>
              <Typography variant="h4" sx={{ fontWeight: 700, color: '#F57C00' }}>
                {totalPending}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card sx={{ borderLeft: '4px solid #2E7D32' }}>
            <CardContent>
              <Typography color="text.secondary" variant="subtitle2" gutterBottom>
                Approved / Locked Records
              </Typography>
              <Typography variant="h4" sx={{ fontWeight: 700, color: '#2E7D32' }}>
                {totalApproved}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Main Charts Workspace */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        {/* Scope Chart */}
        <Grid item xs={12} md={7}>
          <Card sx={{ height: 420 }}>
            <CardContent>
              <Typography variant="h6" gutterBottom sx={{ mb: 3 }}>
                Emissions Profile by Scope (tCO₂e)
              </Typography>
              <Box sx={{ width: '100%', height: 320 }}>
                <ResponsiveContainer>
                  <BarChart data={scopeChartData} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} />
                    <XAxis dataKey="name" />
                    <YAxis />
                    <Tooltip formatter={(value) => [`${Number(value).toFixed(4)} tCO₂e`, 'Emissions']} />
                    <Legend />
                    <Bar dataKey="co2e_tonnes" name="Scope Emissions" fill="#00695C" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </Box>
            </CardContent>
          </Card>
        </Grid>

        {/* Status Pie Chart */}
        <Grid item xs={12} md={5}>
          <Card sx={{ height: 420 }}>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Record Verification Status
              </Typography>
              {statusPieData.length === 0 ? (
                <Box sx={{ display: 'flex', height: 320, alignItems: 'center', justifyContent: 'center' }}>
                  <Typography color="text.secondary">No verification data available</Typography>
                </Box>
              ) : (
                <Box sx={{ width: '100%', height: 320, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <ResponsiveContainer>
                    <PieChart>
                      <Pie
                        data={statusPieData}
                        cx="50%"
                        cy="50%"
                        labelLine={false}
                        outerRadius={95}
                        fill="#8884d8"
                        dataKey="value"
                        label={({ name, percent }) => `${name} (${(percent * 100).toFixed(0)}%)`}
                      >
                        {statusPieData.map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={statusColors[index % statusColors.length]} />
                        ))}
                      </Pie>
                      <Tooltip />
                    </PieChart>
                  </ResponsiveContainer>
                </Box>
              )}
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      <Grid container spacing={3} sx={{ mb: 4 }}>
        {/* Source emissions */}
        <Grid item xs={12} md={5}>
          <Card sx={{ height: 420 }}>
            <CardContent>
              <Typography variant="h6" gutterBottom sx={{ mb: 3 }}>
                Emissions Profile by Source (tCO₂e)
              </Typography>
              <Box sx={{ width: '100%', height: 320 }}>
                <ResponsiveContainer>
                  <BarChart data={sourceChartData} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} />
                    <XAxis dataKey="name" />
                    <YAxis />
                    <Tooltip formatter={(value) => [`${Number(value).toFixed(4)} tCO₂e`, 'Emissions']} />
                    <Legend />
                    <Bar dataKey="co2e_tonnes" name="Source Emissions" fill="#1565C0" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </Box>
            </CardContent>
          </Card>
        </Grid>

        {/* Recent Ingestion Jobs */}
        <Grid item xs={12} md={7}>
          <Card sx={{ height: 420, overflow: 'hidden' }}>
            <CardContent sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
              <Typography variant="h6" gutterBottom sx={{ mb: 2 }}>
                Recent Ingestion Uploads
              </Typography>
              <TableContainer component={Paper} sx={{ flexGrow: 1, boxShadow: 'none', border: '1px solid #E0E0E0' }}>
                <Table stickyHeader size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell sx={{ fontWeight: 600 }}>File Name</TableCell>
                      <TableCell sx={{ fontWeight: 600 }}>Source Type</TableCell>
                      <TableCell sx={{ fontWeight: 600 }}>Rows Ingested</TableCell>
                      <TableCell sx={{ fontWeight: 600 }}>Verification</TableCell>
                      <TableCell sx={{ fontWeight: 600 }}>Uploaded By</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {data.recent_jobs.length === 0 ? (
                      <TableRow>
                        <TableCell colSpan={5} align="center" sx={{ py: 3, color: 'text.secondary' }}>
                          No files uploaded yet. Navigate to "Upload Data" to start.
                        </TableCell>
                      </TableRow>
                    ) : (
                      data.recent_jobs.map((job) => (
                        <TableRow key={job.id} hover>
                          <TableCell sx={{ fontWeight: 500, maxWidth: 180, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                            {job.file_name}
                          </TableCell>
                          <TableCell sx={{ textTransform: 'uppercase' }}>
                            {job.data_source_type}
                          </TableCell>
                          <TableCell>
                            {job.successful_rows} / {job.total_rows}
                          </TableCell>
                          <TableCell>
                            <StatusChip status={job.status} />
                          </TableCell>
                          <TableCell>
                            {job.uploaded_by}
                          </TableCell>
                        </TableRow>
                      ))
                    )}
                  </TableBody>
                </Table>
              </TableContainer>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
};

export default Dashboard;
